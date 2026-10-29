"""
إعدادات التطبيق — كل القيم تُقرأ من متغيرات البيئة (ملف .env)
لا يوجد أي مفتاح أو كلمة مرور مكتوبة هنا مباشرة.
"""
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # عام
    APP_NAME: str = "Lumen"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # قاعدة البيانات (PostgreSQL)
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # رابط الفرونت اند — يُستخدم لبناء روابط تأكيد البريد/إعادة تعيين كلمة المرور
    FRONTEND_URL: str = "http://localhost:5173"
    # عنوان callback الثابت لأداة LTI في الإنتاج؛ يطابق target_link_uri المسجّل.
    LTI_TARGET_LINK_URI: str = ""

    # إيميل — لو SMTP_HOST فاضي، الإيميلات تُطبع باللوق بدل إرسالها فعليًا (وضع تطوير)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@example.com"
    SMTP_USE_TLS: bool = True

    # حماية ضد Brute Force
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # Two Factor Authentication
    TOTP_ISSUER_NAME: str = "Lumen"

    # CORS — 5173 هو منفذ Vite dev server الافتراضي (الفرونت React+Vite)
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # رفع الملفات
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # الاشتراكات والدفع
    PAYMENT_PROVIDER: str = "stripe"  # stripe | paypal
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_WEBHOOK_ID: str = ""
    PAYPAL_API_BASE: str = "https://api-m.sandbox.paypal.com"  # غيّرها للإنتاج: api-m.paypal.com

    # الأداء: Redis للـ caching، Celery+Redis لمهام الخلفية (إرسال الإيميل حاليًا)
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"
    CACHE_TTL_SECONDS: int = 60

    # LTI 1.3 — ربط منصات LMS مثل Moodle/Canvas
    LTI_TOOL_PRIVATE_KEY: str = ""  # PEM لمفتاح RSA خاص — ولّده بـ scripts/generate_lti_key.py
    LTI_TOOL_KID: str = "lumen-key-1"  # معرّف المفتاح بالـ JWKS

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENVIRONMENT.strip().lower() != "production":
            return self

        if self.DEBUG:
            raise ValueError("DEBUG must be false when ENVIRONMENT=production")

        secret = self.JWT_SECRET_KEY.strip()
        lowered_secret = secret.lower()
        if len(secret) < 32 or any(
            marker in lowered_secret
            for marker in ("change_me", "changeme", "replace_me", "example", "your_secret")
        ):
            raise ValueError("JWT_SECRET_KEY must be a strong, non-placeholder secret in production")

        if not self.CORS_ORIGINS or "*" in self.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS must explicitly list trusted origins in production")
        for origin in self.CORS_ORIGINS:
            parsed = urlparse(origin)
            if (
                parsed.scheme != "https"
                or not parsed.netloc
                or parsed.path not in ("", "/")
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Every production CORS origin must be an HTTPS origin without a path")

        frontend = urlparse(self.FRONTEND_URL)
        if frontend.scheme != "https" or not frontend.netloc:
            raise ValueError("FRONTEND_URL must be an absolute HTTPS URL in production")

        if self.LTI_TARGET_LINK_URI:
            target = urlparse(self.LTI_TARGET_LINK_URI)
            if target.scheme != "https" or not target.netloc:
                raise ValueError("LTI_TARGET_LINK_URI must be an absolute HTTPS URL in production")

        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
