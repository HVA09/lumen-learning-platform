"""
مسارات المصادقة: تسجيل، دخول (مع حماية Brute Force)، تجديد التوكن،
تأكيد البريد الإلكتروني، وإعادة تعيين كلمة المرور
"""
from datetime import datetime, timedelta, timezone

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.totp_secrets import (
    TOTPSecretError,
    decrypt_totp_secret,
    encrypt_totp_secret,
    is_encrypted_totp_secret,
)
from app.auth.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.audit import log_event
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.notifications import notify
from app.schemas.auth import (
    EmailVerificationConfirm,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    Token,
)
from app.schemas.user import UserCreate, UserOut
from app.services.email_service import (
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="البريد مسجل مسبقًا")

    # التسجيل العام لا يمنح صلاحيات إدارية؛ إنشاء المدير يجب أن يتم
    # عبر إجراء تهيئة منفصل ومصرّح به خارج نقطة التسجيل العامة.
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_event(db, "register", f"مستخدم جديد: {user.email}", user.id)

    send_verification_email(user.email, create_email_verification_token(user.id))
    send_welcome_email(user.email)
    notify(db, user.id, "أهلًا بك", "تم إنشاء حسابك بنجاح.", "welcome")
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    invalid_credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="بريد إلكتروني أو كلمة مرور غير صحيحة",
    )

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise invalid_credentials_error

    # Disabled accounts must not receive new sessions. Use the same generic
    # response as invalid credentials to avoid disclosing account state.
    if not user.is_active:
        log_event(db, "login_blocked", f"محاولة دخول لحساب معطّل: {user.email}", user.id)
        raise invalid_credentials_error

    # حماية ضد Brute Force: الحساب مقفل مؤقتًا بعد محاولات فاشلة كثيرة
    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        remaining_minutes = int((user.locked_until - now).total_seconds() // 60) + 1
        log_event(db, "login_blocked", f"محاولة دخول لحساب مقفل: {user.email}", user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"الحساب مقفل مؤقتًا، حاول بعد {remaining_minutes} دقيقة",
        )

    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
            db.commit()
            log_event(db, "account_locked", f"تم قفل الحساب مؤقتًا: {user.email}", user.id)
            notify(
                db,
                user.id,
                "قفل الحساب مؤقتًا",
                "محاولات دخول فاشلة متكررة على حسابك — تم قفله مؤقتًا لحمايتك.",
                "security",
            )
        else:
            db.commit()
        log_event(db, "login_failed", f"محاولة دخول فاشلة: {payload.email}", user.id)
        raise invalid_credentials_error

    if user.is_2fa_enabled:
        if not payload.totp_code:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="مطلوب رمز التحقق الثنائي",
            )
        try:
            totp_secret = decrypt_totp_secret(user.totp_secret)
        except TOTPSecretError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="تعذر فك سر التحقق الثنائي؛ تحقق من مفتاح التشفير",
            ) from exc

        if not pyotp.TOTP(totp_secret).verify(payload.totp_code, valid_window=1):
            log_event(db, "2fa_failed", f"رمز 2FA غير صحيح: {user.email}", user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز التحقق الثنائي غير صحيح"
            )

        # Existing accounts may still have plaintext secrets. Upgrade only after
        # a valid TOTP code, so an unauthenticated attempt cannot rewrite secrets.
        if not is_encrypted_totp_secret(user.totp_secret):
            try:
                user.totp_secret = encrypt_totp_secret(totp_secret)
            except TOTPSecretError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="تشفير أسرار التحقق الثنائي غير مُعدّ على الخادم",
                ) from exc

    # دخول ناجح: تصفير عداد المحاولات الفاشلة
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()

    log_event(db, "login", f"تسجيل دخول: {user.email}", user.id)
    return Token(
        access_token=create_access_token(user.id, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
    )


@router.post("/refresh", response_model=Token)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    invalid_token_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token غير صالح"
    )
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise ValueError("ليس refresh token")
        user_id = int(data.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise invalid_token_error

    # تأكد إن المستخدم لسه موجود ومفعّل قبل ما نصدر توكنات جديدة
    user = db.get(User, user_id)
    if (
        user is None
        or not user.is_active
        or data.get("ver", 0) != user.token_version
    ):
        raise invalid_token_error

    return Token(
        access_token=create_access_token(user.id, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
    )


@router.post("/verify-email/request", status_code=status.HTTP_202_ACCEPTED)
def request_email_verification(current_user: User = Depends(get_current_user)):
    if current_user.is_email_verified:
        return {"detail": "البريد مؤكد مسبقًا"}
    send_verification_email(
        current_user.email,
        create_email_verification_token(current_user.id, current_user.token_version),
    )
    return {"detail": "تم إرسال رابط التأكيد"}


@router.post("/verify-email/confirm")
def confirm_email_verification(payload: EmailVerificationConfirm, db: Session = Depends(get_db)):
    invalid_error = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="رابط التأكيد غير صالح أو منتهي"
    )
    try:
        data = decode_token(payload.token)
        if data.get("type") != "email_verify":
            raise ValueError
        user_id = int(data.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise invalid_error

    user = db.get(User, user_id)
    if user is None or data.get("ver", 0) != user.token_version:
        raise invalid_error

    user.is_email_verified = True
    db.commit()
    log_event(db, "email_verified", f"تم تأكيد بريد: {user.email}", user.id)
    return {"detail": "تم تأكيد البريد الإلكتروني بنجاح"}


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    # نرجّع نفس الرد سواء كان الإيميل مسجّل أو لا — عشان ما نكشف إذا حساب موجود
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        send_password_reset_email(
            user.email, create_password_reset_token(user.id, user.token_version)
        )
        log_event(db, "password_reset_requested", f"طلب إعادة تعيين: {user.email}", user.id)
    return {"detail": "لو البريد مسجّل عندنا، وصلته رسالة بخطوات إعادة التعيين"}


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    invalid_error = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="رابط إعادة التعيين غير صالح أو منتهي"
    )
    try:
        data = decode_token(payload.token)
        if data.get("type") != "password_reset":
            raise ValueError
        user_id = int(data.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise invalid_error

    # Lock the row so the same reset token cannot be redeemed concurrently.
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if user is None or data.get("ver", 0) != user.token_version:
        raise invalid_error

    user.hashed_password = hash_password(payload.new_password)
    user.token_version += 1  # invalidate all prior access, refresh, and reset tokens
    # إعادة التعيين إجراء استرجاع مشروع للحساب — نفك أي قفل Brute Force قائم
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    log_event(db, "password_reset", f"تم إعادة تعيين كلمة المرور: {user.email}", user.id)
    return {"detail": "تم تغيير كلمة المرور بنجاح"}
