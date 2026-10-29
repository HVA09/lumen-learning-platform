"""
إعدادات التطبيق — كل القيم تُقرأ من متغيرات البيئة (ملف .env).
لا يوجد أي مفتاح أو كلمة مرور مكتوبة هنا مباشرة.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # عام
    APP_NAME: str = "Lumen"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # قاعدة البيانات (PostgreSQL)
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # رابط الفرونت اند — يُستخدم لبناء روابط تأكيد البريد/إعادة تعيين كلمة المرور
    FRONTEND_URL: str = "http://localhost:5173"

    # LTI 1.3 — في الإنتاج يجب إدراج عناوين target_link_uri المسموح بها بدقة.
    LTI_ALLOWED_TARGET_LINK_URIS: list[str] = []

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

    # CORS — 5173 هو منفذ Vite dev server الافتراضي (Vite dev server)
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

    # LTI 1.3 — مفتاح أداة Lumen الخاص، واسم المفتاح المنشور في JWKS
    LTI_TOOL_PRIVATE_KEY: str = ""
    LTI_TOOL_KID: str = "lumen-key-1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
