import logging

import pytest

from app.config import settings
from app.services.email_service import send_email


def test_production_without_smtp_never_logs_token_bearing_email(monkeypatch, caplog):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    secret_link = "https://learn.example.test/reset-password?token=one-time-secret"

    with caplog.at_level(logging.INFO, logger="app.email"):
        with pytest.raises(RuntimeError, match="SMTP_HOST is required"):
            send_email(
                "student@example.test",
                "إعادة تعيين كلمة المرور",
                secret_link,
            )

    assert "one-time-secret" not in caplog.text
    assert secret_link not in caplog.text


def test_development_without_smtp_keeps_local_email_preview(monkeypatch, caplog):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    preview_link = "http://localhost:5173/verify-email?token=dev-preview"

    with caplog.at_level(logging.INFO, logger="app.email"):
        send_email(
            "student@example.test",
            "تأكيد البريد الإلكتروني",
            preview_link,
        )

    assert preview_link in caplog.text
