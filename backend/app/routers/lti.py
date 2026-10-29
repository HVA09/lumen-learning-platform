"""مسارات تكامل LTI 1.3 مع استخدام state ورمز تبادل أحاديي الاستخدام."""
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, create_refresh_token, hash_password
from app.config import settings
from app.database import get_db
from app.dependencies import require_admin
from app.models.lti import LTIAuthCode, LTIAuthState, LTIPlatform, LTIUserLink
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.lti import LTIExchangeCodeRequest, LTIPlatformCreate, LTIPlatformOut
from app.services.lti_service import (
    LTI_AUTH_CODE_TTL_SECONDS,
    LTI_STATE_TTL_SECONDS,
    build_tool_jwks,
    hash_opaque_token,
    new_nonce,
    verify_platform_id_token,
)

router = APIRouter(prefix="/lti", tags=["LTI"])


@router.post("/platforms", response_model=LTIPlatformOut, status_code=status.HTTP_201_CREATED)
def register_platform(
    payload: LTIPlatformCreate,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """تسجيل منصة LTI جديدة (admin فقط)."""
    platform = LTIPlatform(**payload.model_dump())
    db.add(platform)
    db.commit()
    db.refresh(platform)
    return platform


@router.get("/platforms", response_model=list[LTIPlatformOut])
def list_platforms(_=Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(LTIPlatform).all()


@router.get("/jwks")
def get_jwks():
    return build_tool_jwks()


@router.get("/login")
@router.post("/login")
async def lti_login(
    iss: str = Query(...),
    login_hint: str = Query(...),
    target_link_uri: str = Query(...),
    client_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """يبدأ OIDC بعد مطابقة target_link_uri الثابت عند ضبطه."""
    configured_target = settings.LTI_TARGET_LINK_URI.strip()
    if settings.ENVIRONMENT.strip().lower() == "production" and not configured_target:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LTI is not enabled: configure LTI_TARGET_LINK_URI first.",
        )
    if configured_target and target_link_uri != configured_target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_link_uri غير مسموح")

    platform_query = db.query(LTIPlatform).filter(LTIPlatform.issuer == iss)
    if client_id:
        platform_query = platform_query.filter(LTIPlatform.client_id == client_id)
    matches = platform_query.limit(2).all()
    if len(matches) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="منصة LTI غير مسجّلة أو client_id غير محدد بشكل فريد",
        )
    platform = matches[0]

    nonce = new_nonce()
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    # نظّف الرموز المنتهية حتى لا تنمو جداول التدفق بلا حدود.
    db.query(LTIAuthState).filter(LTIAuthState.expires_at <= now).delete(synchronize_session=False)
    db.query(LTIAuthCode).filter(LTIAuthCode.expires_at <= now).delete(synchronize_session=False)
    db.add(
        LTIAuthState(
            state_hash=hash_opaque_token(state),
            platform_id=platform.id,
            nonce=nonce,
            target_link_uri=target_link_uri,
            expires_at=now + timedelta(seconds=LTI_STATE_TTL_SECONDS),
        )
    )
    db.commit()

    auth_params = {
        "scope": "openid",
        "response_type": "id_token",
        "client_id": platform.client_id,
        "redirect_uri": target_link_uri,
        "login_hint": login_hint,
        "state": state,
        "nonce": nonce,
        "response_mode": "form_post",
        "prompt": "none",
    }
    return RedirectResponse(f"{platform.auth_login_url}?{urlencode(auth_params)}")


@router.post("/launch")
async def lti_launch(
    id_token: str = Form(...),
    state: str = Form(...),
    db: Session = Depends(get_db),
):
    """يتحقق من حالة OIDC غير المستعملة، ثم يصدر رمز تبادل قصير العمر فقط."""
    state_row = (
        db.query(LTIAuthState)
        .filter(LTIAuthState.state_hash == hash_opaque_token(state))
        .with_for_update()
        .first()
    )
    now = datetime.now(timezone.utc)
    if (
        state_row is None
        or state_row.consumed_at is not None
        or state_row.expires_at <= now
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="state غير صالح أو منتهي")

    platform = db.get(LTIPlatform, state_row.platform_id)
    if not platform:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المنصة غير موجودة")

    try:
        claims = await verify_platform_id_token(id_token, platform, state_row.nonce)
    except Exception:
        # لا نعيد تفاصيل التحقق أو معلومات المفاتيح إلى العميل.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="تعذّر التحقق من تسجيل الدخول عبر منصة التعليم",
        )

    lti_subject = claims["sub"]
    link = (
        db.query(LTIUserLink)
        .filter(LTIUserLink.platform_id == platform.id, LTIUserLink.lti_subject == lti_subject)
        .first()
    )

    if link:
        user = db.get(User, link.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="حساب LTI غير متاح")
    else:
        claimed_email = claims.get("email")
        email_verified = claims.get("email_verified") is True
        if claimed_email and email_verified:
            email = claimed_email.strip().lower()
            existing = db.query(User).filter(func.lower(User.email) == email).first()
            if existing:
                # لا نربط حسابًا محليًا موجودًا تلقائيًا اعتمادًا على البريد.
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="يوجد حساب بهذا البريد. سجّل الدخول بالطريقة المعتادة قبل إعداد ربط الحسابات.",
                )
        else:
            email = f"lti_{platform.id}_{hash_opaque_token(lti_subject)[:32]}@lti.local"

        user = User(
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            full_name=claims.get("name"),
            is_email_verified=email_verified,
        )
        db.add(user)
        db.flush()
        db.add(LTIUserLink(platform_id=platform.id, lti_subject=lti_subject, user_id=user.id))

    exchange_code = secrets.token_urlsafe(32)
    db.add(
        LTIAuthCode(
            code_hash=hash_opaque_token(exchange_code),
            user_id=user.id,
            expires_at=now + timedelta(seconds=LTI_AUTH_CODE_TTL_SECONDS),
        )
    )
    state_row.consumed_at = now
    db.commit()

    redirect_url = (
        f"{settings.FRONTEND_URL.rstrip('/')}/lti-callback?"
        f"{urlencode({'code': exchange_code})}"
    )
    return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)


@router.post("/exchange-code", response_model=Token)
def exchange_lti_code(
    payload: LTIExchangeCodeRequest,
    db: Session = Depends(get_db),
):
    """يستبدل رمزًا عشوائيًا قصير العمر برموز JWT مرة واحدة فقط."""
    auth_code = (
        db.query(LTIAuthCode)
        .filter(LTIAuthCode.code_hash == hash_opaque_token(payload.code))
        .with_for_update()
        .first()
    )
    now = datetime.now(timezone.utc)
    if (
        auth_code is None
        or auth_code.consumed_at is not None
        or auth_code.expires_at <= now
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز الدخول غير صالح أو منتهي")

    user = db.get(User, auth_code.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="حساب الدخول غير متاح")

    auth_code.consumed_at = now
    db.commit()
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
