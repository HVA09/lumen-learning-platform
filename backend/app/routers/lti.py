"""مسارات تكامل LTI 1.3 مع استخدام state ورمز تبادل أحاديي الاستخدام."""
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.cookies import (
    create_csrf_token,
    set_auth_cookies,
    verify_csrf_request,
)
from app.auth.security import hash_password
from app.auth.sessions import create_browser_session
from app.config import settings
from app.database import get_db
from app.dependencies import require_admin
from app.models.assignment import Assignment
from app.models.lti import (
    LTIAuthCode, LTIAuthState, LTIPlatform, LTIUserLink,
    LTIAssignmentLink, LTIAGSGradeEvent,
)
from app.models.user import User
from app.schemas.lti import (
    LTIExchangeCodeRequest, LTIPlatformCreate, LTIPlatformOut,
    LTIAssignmentLinkCreate, LTIAssignmentLinkOut, LTIAGSGradeEventOut,
)
from app.services.lti_service import (
    LTI_AUTH_CODE_TTL_SECONDS,
    LTI_STATE_TTL_SECONDS,
    build_tool_jwks,
    record_lti_ags_launch_context,
    hash_opaque_token,
    new_nonce,
    verify_platform_id_token,
    validate_lti_platform_endpoint_url,
)

router = APIRouter(prefix="/lti", tags=["LTI"])


def _no_store_redirect(url: str) -> RedirectResponse:
    return RedirectResponse(
        url,
        status_code=status.HTTP_302_FOUND,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
        },
    )


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




@router.post(
    "/assignment-links",
    response_model=LTIAssignmentLinkOut,
    status_code=status.HTTP_201_CREATED,
)
def register_assignment_link(
    payload: LTIAssignmentLinkCreate,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only mapping between a Lumen assignment and an LMS resource link."""
    platform = db.get(LTIPlatform, payload.platform_id)
    assignment = db.get(Assignment, payload.assignment_id)
    if platform is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="منصة LTI غير موجودة")
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الواجب غير موجود")
    duplicate = (
        db.query(LTIAssignmentLink)
        .filter(
            LTIAssignmentLink.platform_id == platform.id,
            LTIAssignmentLink.deployment_id == platform.deployment_id,
            LTIAssignmentLink.resource_link_id == payload.resource_link_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="رابط المورد مسجل مسبقًا")
    mapping = LTIAssignmentLink(
        platform_id=platform.id,
        assignment_id=assignment.id,
        deployment_id=platform.deployment_id,
        resource_link_id=payload.resource_link_id,
        score_maximum=payload.score_maximum,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.get("/assignment-links", response_model=list[LTIAssignmentLinkOut])
def list_assignment_links(_=Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(LTIAssignmentLink).order_by(LTIAssignmentLink.id.desc()).all()


@router.get("/grade-events", response_model=list[LTIAGSGradeEventOut])
def list_grade_events(_=Depends(require_admin), db: Session = Depends(get_db)):
    """Expose delivery state without returning learner identifiers or access tokens."""
    return (
        db.query(LTIAGSGradeEvent)
        .order_by(LTIAGSGradeEvent.id.desc())
        .limit(200)
        .all()
    )


@router.post("/grade-events/{event_id}/retry", response_model=LTIAGSGradeEventOut)
def retry_grade_event(
    event_id: int,
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = db.get(LTIAGSGradeEvent, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="حدث التقييم غير موجود")
    if event.status != "dead":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="إعادة المحاولة اليدوية متاحة للأحداث المتوقفة فقط",
        )
    event.status = "pending"
    event.attempts = 0
    event.last_error = None
    event.locked_until = None
    event.next_attempt_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event


@router.get("/jwks")
def get_jwks():
    return build_tool_jwks()


def _start_lti_login(
    iss: str,
    login_hint: str,
    target_link_uri: str,
    client_id: str | None,
    lti_message_hint: str | None,
    lti_deployment_id: str | None,
    db: Session,
) -> RedirectResponse:
    """Shared OIDC initiation; retain the platform hint exactly as received."""
    target = urlsplit(target_link_uri)
    if (
        target.scheme not in {"https", "http"}
        or not target.netloc
        or target.username is not None
        or target.password is not None
        or target.fragment
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="target_link_uri غير صالح"
        )
    if target.scheme == "http" and target.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يجب استخدام HTTPS في target_link_uri خارج التطوير المحلي",
        )

    configured_target = settings.LTI_TARGET_LINK_URI.strip()
    if settings.ENVIRONMENT.strip().lower() == "production" and not configured_target:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LTI is not enabled: configure LTI_TARGET_LINK_URI first.",
        )
    if configured_target and target_link_uri != configured_target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="target_link_uri غير مسموح"
        )

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
    try:
        validate_lti_platform_endpoint_url(platform.auth_login_url)
        validate_lti_platform_endpoint_url(platform.auth_token_url)
        validate_lti_platform_endpoint_url(platform.jwks_url)
        validate_lti_platform_endpoint_url(platform.issuer)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="بيانات عناوين منصة LTI غير آمنة أو غير صالحة",
        )
    if lti_deployment_id is not None and lti_deployment_id != platform.deployment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lti_deployment_id لا يطابق عملية النشر المسجلة",
        )

    nonce = new_nonce()
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.query(LTIAuthState).filter(
        LTIAuthState.expires_at <= now
    ).delete(synchronize_session=False)
    db.query(LTIAuthCode).filter(
        LTIAuthCode.expires_at <= now
    ).delete(synchronize_session=False)
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
    if lti_message_hint is not None:
        auth_params["lti_message_hint"] = lti_message_hint
    return _no_store_redirect(f"{platform.auth_login_url}?{urlencode(auth_params)}")


@router.get("/login")
def lti_login_get(
    iss: str = Query(..., min_length=1, max_length=500),
    login_hint: str = Query(..., min_length=1, max_length=2000),
    target_link_uri: str = Query(..., min_length=1, max_length=1000),
    client_id: str | None = Query(None, max_length=255),
    lti_message_hint: str | None = Query(None, max_length=2000),
    lti_deployment_id: str | None = Query(None, max_length=255),
    db: Session = Depends(get_db),
):
    """دعم OIDC initiation عبر GET، مع حفظ lti_message_hint كما ورد."""
    return _start_lti_login(
        iss, login_hint, target_link_uri, client_id,
        lti_message_hint, lti_deployment_id, db
    )


@router.post("/login")
def lti_login_post(
    iss: str = Form(..., min_length=1, max_length=500),
    login_hint: str = Form(..., min_length=1, max_length=2000),
    target_link_uri: str = Form(..., min_length=1, max_length=1000),
    client_id: str | None = Form(None, max_length=255),
    lti_message_hint: str | None = Form(None, max_length=2000),
    lti_deployment_id: str | None = Form(None, max_length=255),
    db: Session = Depends(get_db),
):
    """دعم OIDC initiation عبر form POST، مع حفظ lti_message_hint كما ورد."""
    return _start_lti_login(
        iss, login_hint, target_link_uri, client_id,
        lti_message_hint, lti_deployment_id, db
    )


@router.post("/launch")
async def lti_launch(
    id_token: str = Form(..., max_length=20000),
    state: str = Form(..., min_length=20, max_length=256),
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
        claims = await verify_platform_id_token(
            id_token, platform, state_row.nonce, state_row.target_link_uri
        )
    except Exception:
        # لا نعيد تفاصيل التحقق أو معلومات المفاتيح إلى العميل.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="تعذّر التحقق من تسجيل الدخول عبر منصة التعليم",
        )

    record_lti_ags_launch_context(db, platform, claims)

    lti_subject = claims.get("sub")
    if not isinstance(lti_subject, str) or not lti_subject or len(lti_subject) > 255:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="معرّف مستخدم LTI غير صالح")
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
            token_version=user.token_version,
            expires_at=now + timedelta(seconds=LTI_AUTH_CODE_TTL_SECONDS),
        )
    )
    state_row.consumed_at = now
    db.commit()

    # Put the one-time code in the URL fragment: browsers do not send fragments
    # to web servers or include them in HTTP Referer headers.
    redirect_url = (
        f"{settings.FRONTEND_URL.rstrip('/')}/lti-callback#"
        f"{urlencode({'code': exchange_code})}"
    )
    return _no_store_redirect(redirect_url)


@router.post("/exchange-code")
def exchange_lti_code(
    payload: LTIExchangeCodeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    origin = request.headers.get("origin")
    if origin:
        if origin not in settings.CORS_ORIGINS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Untrusted request origin")
        verify_csrf_request(request)
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
    if (
        user is None
        or not user.is_active
        or user.token_version != auth_code.token_version
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="حساب الدخول غير متاح")

    auth_code.consumed_at = now
    access_token, refresh_token, _ = create_browser_session(db, user)
    db.commit()
    csrf_token = create_csrf_token()
    set_auth_cookies(response, access_token, refresh_token, csrf_token)
    return {"authenticated": True, "csrf_token": csrf_token}
