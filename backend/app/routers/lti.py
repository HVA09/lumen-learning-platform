"""
مسارات LTI 1.3: OIDC login، استقبال launch، ونقطة تبادل رمز مؤقت لجلسة Lumen.
لا تُرسل access/refresh tokens عبر URL مطلقًا.
"""
import secrets
from hashlib import sha256
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, create_refresh_token, hash_password
from app.config import settings
from app.database import get_db
from app.dependencies import require_admin
from app.models.lti import LTIPlatform, LTIUserLink
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.lti import LTIExchangeRequest, LTIPlatformCreate, LTIPlatformOut
from app.services.lti_service import (
    build_tool_jwks,
    consume_login_state,
    consume_lti_auth_code,
    create_login_state,
    create_lti_auth_code,
    get_login_state,
    new_nonce,
    verify_platform_id_token,
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
    """تسجيل منصة LTI جديدة — admin فقط."""
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


async def _start_lti_login(
    iss: str,
    login_hint: str,
    target_link_uri: str,
    client_id: str | None,
    lti_message_hint: str | None,
    lti_deployment_id: str | None,
    db: Session,
):
    """خطوة OIDC الأولى — تنشئ state عشوائيًا مرتبطًا بالمنصة والـ nonce."""
    platform_query = db.query(LTIPlatform).filter(LTIPlatform.issuer == iss)
    if client_id:
        platform_query = platform_query.filter(LTIPlatform.client_id == client_id)
    platforms = platform_query.limit(2).all()
    if len(platforms) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="منصة LTI غير مسجلة أو أن بيانات المنصة غير محددة بشكل كافٍ",
        )
    platform = platforms[0]
    if lti_deployment_id is not None and lti_deployment_id != platform.deployment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lti_deployment_id لا يطابق عملية النشر المسجلة",
        )

    target = urlsplit(target_link_uri)
    if (
        target.scheme not in {"https", "http"}
        or not target.netloc
        or target.username is not None
        or target.password is not None
        or target.fragment
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_link_uri غير صالح",
        )
    if target.scheme == "http" and target.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يجب استخدام HTTPS في target_link_uri خارج التطوير المحلي",
        )
    if (
        settings.ENVIRONMENT.lower() not in {"development", "test", "testing"}
        and not settings.LTI_ALLOWED_TARGET_LINK_URIS
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="لم تُضبط قائمة target_link_uri المسموح بها لـ LTI في بيئة الإنتاج",
        )
    if (
        settings.LTI_ALLOWED_TARGET_LINK_URIS
        and target_link_uri not in settings.LTI_ALLOWED_TARGET_LINK_URIS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_link_uri غير مسموح به",
        )

    nonce = new_nonce()
    state = create_login_state(db, platform.id, nonce, target_link_uri)
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
        # LTI 1.3 requires this opaque platform value to be returned unchanged.
        auth_params["lti_message_hint"] = lti_message_hint
    return _no_store_redirect(f"{platform.auth_login_url}?{urlencode(auth_params)}")


@router.get("/login")
async def lti_login_get(
    iss: str = Query(..., min_length=1, max_length=500),
    login_hint: str = Query(..., min_length=1, max_length=2000),
    target_link_uri: str = Query(..., min_length=1, max_length=1000),
    client_id: str | None = Query(None, max_length=255),
    lti_message_hint: str | None = Query(None, max_length=2000),
    lti_deployment_id: str | None = Query(None, max_length=255),
    db: Session = Depends(get_db),
):
    """دعم OIDC third-party initiated login الذي يرسل الحقول في query string."""
    return await _start_lti_login(
        iss, login_hint, target_link_uri, client_id, lti_message_hint, lti_deployment_id, db
    )


@router.post("/login")
async def lti_login_post(
    iss: str = Form(..., min_length=1, max_length=500),
    login_hint: str = Form(..., min_length=1, max_length=2000),
    target_link_uri: str = Form(..., min_length=1, max_length=1000),
    client_id: str | None = Form(None, max_length=255),
    lti_message_hint: str | None = Form(None, max_length=2000),
    lti_deployment_id: str | None = Form(None, max_length=255),
    db: Session = Depends(get_db),
):
    """دعم OIDC third-party initiated login الذي يرسل الحقول عبر form POST."""
    return await _start_lti_login(
        iss, login_hint, target_link_uri, client_id, lti_message_hint, lti_deployment_id, db
    )


@router.post("/launch")
async def lti_launch(
    id_token: str = Form(..., max_length=20000),
    state: str = Form(..., min_length=20, max_length=256),
    db: Session = Depends(get_db),
):
    """يتحقق من launch، يستهلك state مرة واحدة، ثم يعيد رمز تبادل محدود الصلاحية."""
    try:
        state_record = get_login_state(db, state)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="state غير صالح أو منتهي أو مستهلك"
        )

    platform = db.get(LTIPlatform, state_record.platform_id)
    if not platform:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المنصة غير موجودة")

    try:
        claims = await verify_platform_id_token(
            id_token, platform, state_record.nonce, state_record.target_link_uri
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="تعذّر التحقق من بيانات الدخول المرسلة من منصة التعليم",
        )

    # التحديث ذري لمنع استخدام state نفسه في طلبين متزامنين.
    if not consume_login_state(db, state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="state استُخدم مسبقًا أو انتهت صلاحيته"
        )

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
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="حساب Lumen غير متاح")
    else:
        # Do not attach an unlinked LTI subject to an existing local account by
        # email alone. Email claims may be absent/unverified or controlled by
        # the LMS tenant; account linking must be an explicit authenticated flow.
        subject_digest = sha256(lti_subject.encode("utf-8")).hexdigest()
        identity_email = f"lti_{platform.id}_{subject_digest[:48]}@lti.example.com"
        user = db.query(User).filter(User.email == identity_email).first()
        if not user:
            display_name = claims.get("name")
            if not isinstance(display_name, str):
                display_name = None
            else:
                display_name = display_name[:255]
            user = User(
                email=identity_email,
                hashed_password=hash_password(secrets.token_urlsafe(32)),
                full_name=display_name,
                is_email_verified=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        db.add(LTIUserLink(platform_id=platform.id, lti_subject=lti_subject, user_id=user.id))
        db.commit()

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="حساب Lumen غير مفعّل")

    code = create_lti_auth_code(db, user.id, user.token_version)
    # Fragment لا يُرسل في طلب HTTP الأول إلى خادم الواجهة الأمامية أو في Referer.
    redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/lti-callback#code={code}"
    return _no_store_redirect(redirect_url)


@router.post("/exchange", response_model=Token)
def exchange_lti_code(
    payload: LTIExchangeRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """يستبدل رمزًا مؤقتًا بأقل صلاحيات ممكنة: access/refresh tokens لا تظهر في URL."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    consumed_code = consume_lti_auth_code(db, payload.code)
    if consumed_code is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رمز الدخول غير صالح أو منتهي أو استُخدم مسبقًا",
        )
    user_id, code_token_version = consumed_code
    user = db.get(User, user_id)
    if (
        user is None
        or not user.is_active
        or user.token_version != code_token_version
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="حساب Lumen غير متاح"
        )
    return Token(
        access_token=create_access_token(user.id, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
    )
