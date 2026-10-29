"""
مسارات LTI 1.3: تسجيل دخول OIDC (يبدأه Moodle/Canvas)، استقبال الـ launch،
ونشر مفاتيح أداتنا العامة (JWKS).

⚠️ تطبيق متوافق مع مواصفة LTI 1.3 الرسمية، لكن يحتاج اختبار فعلي مقابل
منصة LMS حقيقية (Moodle sandbox مثلًا) قبل الإنتاج — راجع README لخطوات التسجيل.
"""
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, create_refresh_token, hash_password
from app.dependencies import require_admin
from app.schemas.lti import LTIPlatformCreate, LTIPlatformOut
from app.config import settings
from app.database import get_db
from app.models.lti import LTIPlatform, LTIUserLink
from app.models.user import User
from app.services.lti_service import (
    build_tool_jwks,
    decode_login_state,
    encode_login_state,
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
    """تسجيل منصة LTI جديدة (admin فقط) — القيم تجيك من لوحة تسجيل الأداة بـ Moodle/Canvas"""
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
    """خطوة OIDC الأولى — Moodle/Canvas يستدعيها قبل ما يوجّه المستخدم لصفحة الأداة"""
    platform = (
        db.query(LTIPlatform)
        .filter(LTIPlatform.issuer == iss, LTIPlatform.client_id == (client_id or LTIPlatform.client_id))
        .first()
    )
    if not platform:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="منصة LTI غير مسجّلة — سجّلها أول بجدول lti_platforms",
        )

    nonce = new_nonce()
    state = encode_login_state(platform.id, nonce, target_link_uri)

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
    from urllib.parse import urlencode

    return RedirectResponse(f"{platform.auth_login_url}?{urlencode(auth_params)}")


@router.post("/launch")
async def lti_launch(
    id_token: str = Form(...),
    state: str = Form(...),
    db: Session = Depends(get_db),
):
    """الخطوة الأخيرة — المنصة ترسل id_token موقّع بعد ما المستخدم يتصادق عندها"""
    try:
        state_data = decode_login_state(state)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="state غير صالح أو منتهي")

    platform = db.get(LTIPlatform, state_data["platform_id"])
    if not platform:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المنصة غير موجودة")

    try:
        claims = await verify_platform_id_token(id_token, platform, state_data["nonce"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"تعذّر التحقق من id_token: {exc}"
        )

    lti_subject = claims["sub"]
    link = (
        db.query(LTIUserLink)
        .filter(LTIUserLink.platform_id == platform.id, LTIUserLink.lti_subject == lti_subject)
        .first()
    )

    if link:
        user = db.get(User, link.user_id)
    else:
        email = claims.get("email") or f"lti_{platform.id}_{lti_subject}@lti.local"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                hashed_password=hash_password(secrets.token_urlsafe(32)),  # ما يُستخدم أبدًا — الدخول عبر LTI بس
                full_name=claims.get("name"),
                is_email_verified=True,  # موثّق أصلًا عبر منصة LMS
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        db.add(LTIUserLink(platform_id=platform.id, lti_subject=lti_subject, user_id=user.id))
        db.commit()

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    redirect_url = (
        f"{settings.FRONTEND_URL}/lti-callback"
        f"?access_token={access_token}&refresh_token={refresh_token}"
    )
    return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)
