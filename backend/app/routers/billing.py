"""
مسارات الاشتراكات والدفع: عرض الخطط، بدء الدفع، إلغاء الاشتراك، واستقبال webhooks
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import log_event
from app.cache import cache_get, cache_set
from app.config import settings as app_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.logging_config import get_logger
from app.models.plan import Plan
from app.models.processed_webhook_event import ProcessedWebhookEvent
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.notifications import notify_realtime
from app.schemas.billing import CheckoutRequest, CheckoutResponse, PlanOut, SubscriptionOut
from app.services.email_service import send_subscription_activated_email, send_subscription_canceled_email
from app.services.payment_providers.factory import get_payment_provider
from app.services.payment_providers.paypal_provider import PayPalProvider

router = APIRouter(prefix="/billing", tags=["Billing"])
logger = get_logger("billing")


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    cache_key = "billing:plans"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    plans = db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.price_cents).all()
    result = [PlanOut.model_validate(p).model_dump() for p in plans]
    cache_set(cache_key, result, app_settings.CACHE_TTL_SECONDS)
    return result


@router.get("/subscription", response_model=SubscriptionOut | None)
def get_my_subscription(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(Subscription).filter(Subscription.user_id == current_user.id).first()


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.get(Plan, payload.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الخطة غير موجودة")

    # Redirect destinations are controlled by trusted server configuration, not the client.
    frontend_url = app_settings.FRONTEND_URL.rstrip("/")
    success_url = f"{frontend_url}/billing/success"
    cancel_url = f"{frontend_url}/billing/cancel"

    provider = get_payment_provider()
    try:
        result = await provider.create_checkout_session(
            user_id=current_user.id,
            user_email=current_user.email,
            plan=plan,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except Exception as exc:
        logger.exception("فشل إنشاء جلسة دفع للمستخدم %s", current_user.email)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="تعذر بدء عملية الدفع"
        ) from exc

    if not result.checkout_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="لم يصل رابط دفع من مزوّد الدفع"
        )
    return CheckoutResponse(checkout_url=result.checkout_url)


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="لا يوجد اشتراك")

    provider = get_payment_provider()
    try:
        await provider.cancel_subscription(subscription.provider_subscription_id)
    except Exception as exc:
        logger.exception("فشل إلغاء اشتراك %s", subscription.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="تعذر إلغاء الاشتراك عند المزوّد"
        ) from exc

    subscription.status = SubscriptionStatus.canceled
    db.commit()
    log_event(db, "subscription_canceled", f"إلغاء اشتراك: {current_user.email}", current_user.id)
    send_subscription_canceled_email(current_user.email)
    await notify_realtime(
        db, current_user.id, "تم إلغاء اشتراكك", "رجعت لحدود الخطة المجانية.", "billing"
    )
    return {"detail": "تم إلغاء الاشتراك"}


def _claim_webhook_event(event, provider_name: str, db: Session) -> bool:
    """Atomically claim an event ID. The unique key is scoped to the provider."""
    event_id = (event.event_id or "").strip()
    if not event_id or len(event_id) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="معرّف حدث الدفع مفقود أو غير صالح",
        )

    try:
        # A savepoint lets us handle a concurrent duplicate without poisoning the
        # request's outer transaction. The unique constraint is the final arbiter.
        with db.begin_nested():
            db.add(
                ProcessedWebhookEvent(
                    provider=provider_name,
                    provider_event_id=event_id,
                    event_type=event.event_type[:100],
                )
            )
            db.flush()
    except IntegrityError:
        logger.info("تجاهل حدث دفع مكرر من %s: %s", provider_name, event_id)
        return False

    return True


def _safe_billing_audit(
    db: Session, event_type: str, description: str, user_id: int
) -> None:
    try:
        log_event(db, event_type, description, user_id)
    except Exception:
        db.rollback()
        logger.exception("تعذر حفظ سجل تدقيق حدث الدفع %s", event_type)


async def _safe_billing_notification(
    db: Session, user_id: int, title: str, body: str
) -> None:
    try:
        await notify_realtime(db, user_id, title, body, "billing")
    except Exception:
        db.rollback()
        logger.exception("تعذر إنشاء أو بث إشعار الدفع للمستخدم %s", user_id)


async def _apply_webhook_event(event, provider_name: str, db: Session) -> bool:
    """Apply a verified event. Return False when a supported event cannot yet be matched."""
    if event.event_type == "checkout_completed":
        if not (
            event.client_reference_id
            and event.plan_id
            and event.provider_subscription_id
        ):
            return False
        try:
            user_id = int(event.client_reference_id)
            plan_id = int(event.plan_id)
        except (TypeError, ValueError):
            return False

        user = db.get(User, user_id)
        plan = db.get(Plan, plan_id)
        if not user or not plan:
            return False

        existing = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        should_notify = (
            existing is None
            or existing.status != SubscriptionStatus.active
            or existing.plan_id != plan_id
            or existing.provider != provider_name
            or existing.provider_subscription_id != event.provider_subscription_id
        )
        if existing:
            existing.plan_id = plan_id
            existing.provider = provider_name
            existing.provider_subscription_id = event.provider_subscription_id
            existing.provider_customer_id = event.provider_customer_id
            existing.status = SubscriptionStatus.active
        else:
            db.add(
                Subscription(
                    user_id=user_id,
                    plan_id=plan_id,
                    provider=provider_name,
                    provider_subscription_id=event.provider_subscription_id,
                    provider_customer_id=event.provider_customer_id,
                    status=SubscriptionStatus.active,
                )
            )

        # Commit the event receipt and entitlement change in the same transaction.
        db.commit()
        _safe_billing_audit(
            db,
            "subscription_activated",
            f"تفعيل اشتراك عبر {provider_name}",
            user_id,
        )

        if should_notify:
            try:
                send_subscription_activated_email(user.email, plan.name)
            except Exception:
                logger.exception("تعذر إرسال رسالة تفعيل الاشتراك للمستخدم %s", user_id)
            await _safe_billing_notification(
                db, user_id, "تم تفعيل اشتراكك", f"خطتك الحالية الآن: {plan.name}"
            )
        return True

    if event.event_type in ("subscription_updated", "subscription_canceled"):
        if not event.provider_subscription_id or not event.status:
            return False

        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.provider == provider_name,
                Subscription.provider_subscription_id == event.provider_subscription_id,
            )
            .first()
        )
        if not subscription:
            # Do not permanently claim an event that arrived before its checkout
            # record; return a retryable response so the provider can deliver it again.
            return False

        try:
            new_status = SubscriptionStatus(event.status)
        except ValueError:
            logger.warning(
                "حالة اشتراك غير معروفة من %s: %s", provider_name, event.status
            )
            return True

        status_changed = subscription.status != new_status
        subscription.status = new_status
        subscription.provider_customer_id = (
            event.provider_customer_id or subscription.provider_customer_id
        )
        user_id = subscription.user_id
        db.commit()

        if status_changed:
            _safe_billing_audit(
                db,
                "subscription_status_changed",
                f"اشتراك #{subscription.id} صار: {new_status.value}",
                user_id,
            )
            if new_status == SubscriptionStatus.canceled:
                user = db.get(User, user_id)
                if user:
                    try:
                        send_subscription_canceled_email(user.email)
                    except Exception:
                        logger.exception(
                            "تعذر إرسال رسالة إلغاء الاشتراك للمستخدم %s", user_id
                        )
                    await _safe_billing_notification(
                        db,
                        user_id,
                        "تم إلغاء اشتراكك",
                        "رجعت لحدود الخطة المجانية.",
                    )
        return True

    # Unknown but correctly signed provider events are recorded and acknowledged.
    return True


async def _process_verified_webhook_event(event, provider_name: str, db: Session) -> dict:
    if not _claim_webhook_event(event, provider_name, db):
        return {"received": True, "duplicate": True}

    try:
        handled = await _apply_webhook_event(event, provider_name, db)
        if not handled:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="تعذر ربط حدث الدفع باشتراك حالي؛ سيعيد مزود الدفع المحاولة",
            )
        # Also persist verified, intentionally ignored event types.
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("فشل تطبيق حدث webhook من %s", provider_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="تعذر معالجة حدث الدفع",
        ) from exc

    return {"received": True, "duplicate": False}


@router.post("/webhook/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    provider = get_payment_provider()
    try:
        event = provider.verify_webhook(payload, dict(request.headers))
    except Exception as exc:
        logger.warning("توقيع Stripe webhook غير صالح: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="توقيع غير صالح")

    return await _process_verified_webhook_event(event, "stripe", db)


@router.post("/webhook/paypal", include_in_schema=False)
async def paypal_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    provider = get_payment_provider()
    if not isinstance(provider, PayPalProvider):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PayPal غير مفعّل")

    try:
        event = await provider.verify_webhook_async(payload, dict(request.headers))
    except Exception as exc:
        logger.warning("توقيع PayPal webhook غير صالح: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="توقيع غير صالح")

    return await _process_verified_webhook_event(event, "paypal", db)
