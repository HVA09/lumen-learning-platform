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


class FakeSMTP:
    def __init__(self, failure_stage=None):
        self.failure_stage = failure_stage
        self.calls = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True
        return False

    def _record(self, stage, *args):
        self.calls.append((stage, args))
        if self.failure_stage == stage:
            raise smtplib.SMTPException(f"simulated {stage} failure")

    def starttls(self):
        self._record("starttls")

    def login(self, username, password):
        self._record("login", username, password)

    def send_message(self, message):
        self._record("send_message", message)


def _configure_smtp(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "noreply@example.test")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(settings, "SMTP_USER", "smtp-user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "smtp-password-for-test")


def test_smtp_delivery_uses_tls_auth_and_expected_message(monkeypatch):
    _configure_smtp(monkeypatch)
    server = FakeSMTP()
    smtp_connections = []

    def fake_smtp(host, port):
        smtp_connections.append((host, port))
        return server

    monkeypatch.setattr(email_service.smtplib, "SMTP", fake_smtp)

    email_service.send_email(
        "student@example.test",
        "Test subject",
        "A test message body",
    )

    assert smtp_connections == [("smtp.example.test", 587)]
    assert [stage for stage, _ in server.calls] == [
        "starttls",
        "login",
        "send_message",
    ]
    assert server.calls[1][1] == ("smtp-user", "smtp-password-for-test")
    message = server.calls[2][1][0]
    assert message["From"] == "noreply@example.test"
    assert message["To"] == "student@example.test"
    assert message["Subject"] == "Test subject"
    assert "A test message body" in message.get_content()
    assert server.closed


def test_smtp_delivery_skips_authentication_without_credentials(monkeypatch):
    _configure_smtp(monkeypatch)
    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
    server = FakeSMTP()
    monkeypatch.setattr(email_service.smtplib, "SMTP", lambda host, port: server)

    email_service.send_email(
        "student@example.test",
        "Test subject",
        "A test message body",
    )

    assert [stage for stage, _ in server.calls] == ["starttls", "send_message"]
    assert server.closed


@pytest.mark.parametrize(
    "failure_stage",
    ["connect", "starttls", "login", "send_message"],
)
def test_smtp_transport_failures_propagate_without_logging_message_body(
    monkeypatch, failure_stage
):
    _configure_smtp(monkeypatch)
    server = FakeSMTP(failure_stage if failure_stage != "connect" else None)
    logged_messages = []

    def fake_smtp(host, port):
        if failure_stage == "connect":
            raise smtplib.SMTPException("simulated connection failure")
        return server

    monkeypatch.setattr(email_service.smtplib, "SMTP", fake_smtp)
    monkeypatch.setattr(
        email_service.logger,
        "info",
        lambda message, *args: logged_messages.append(message % args),
    )
    monkeypatch.setattr(
        email_service.logger,
        "error",
        lambda message, *args: logged_messages.append(message % args),
    )

    with pytest.raises(smtplib.SMTPException):
        email_service.send_email(
            "student@example.test",
            "Password reset",
            "message-body-marker",
        )

    assert logged_messages == []
    if failure_stage != "connect":
        assert server.closed
    assert "message-body-marker" not in "\n".join(logged_messages)
