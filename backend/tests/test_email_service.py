import pytest

from app.config import settings
from app.services import email_service


def test_production_without_smtp_never_logs_token_bearing_email(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    secret_link = "https://learn.example.test/reset-password?token=one-time-secret"
    logged_messages = []
    monkeypatch.setattr(
        email_service.logger,
        "error",
        lambda message, *args: logged_messages.append(message % args),
    )

    with pytest.raises(RuntimeError, match="SMTP_HOST is required"):
        email_service.send_email(
            "student@example.test",
            "إعادة تعيين كلمة المرور",
            secret_link,
        )

    combined_log = "\n".join(logged_messages)
    assert "one-time-secret" not in combined_log
    assert secret_link not in combined_log


def test_development_without_smtp_keeps_local_email_preview(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    preview_link = "http://localhost:5173/verify-email?token=dev-preview"
    logged_messages = []
    monkeypatch.setattr(
        email_service.logger,
        "info",
        lambda message, *args: logged_messages.append(message % args),
    )

    email_service.send_email(
        "student@example.test",
        "تأكيد البريد الإلكتروني",
        preview_link,
    )

    assert preview_link in "\n".join(logged_messages)
