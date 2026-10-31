"""
اختبارات Two Factor Authentication (TOTP)
"""
import pyotp

from app.auth.totp_secrets import TOTP_SECRET_PREFIX, decrypt_totp_secret
from app.models.user import User


def _register_and_login(client, email="twofa@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.json()["access_token"]


def test_setup_returns_secret_and_qr_code(client, db_session):
    token = _register_and_login(client)
    response = client.post(
        "/auth/2fa/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["secret"]) > 0
    assert len(body["qr_code_base64"]) > 0

    user = db_session.query(User).filter(User.email == "twofa@example.com").one()
    assert user.totp_secret.startswith(TOTP_SECRET_PREFIX)
    assert user.totp_secret != body["secret"]
    assert decrypt_totp_secret(user.totp_secret) == body["secret"]


def test_enable_with_correct_code_succeeds(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    setup_response = client.post("/auth/2fa/setup", headers=headers)
    secret = setup_response.json()["secret"]
    valid_code = pyotp.TOTP(secret).now()

    response = client.post("/auth/2fa/enable", json={"totp_code": valid_code}, headers=headers)
    assert response.status_code == 200


def test_enable_with_wrong_code_fails(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/auth/2fa/setup", headers=headers)
    response = client.post("/auth/2fa/enable", json={"totp_code": "000000"}, headers=headers)
    assert response.status_code == 401


def test_login_with_2fa_enabled_requires_code(client):
    token = _register_and_login(client, "needs2fa@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    setup_response = client.post("/auth/2fa/setup", headers=headers)
    secret = setup_response.json()["secret"]
    client.post("/auth/2fa/enable", json={"totp_code": pyotp.TOTP(secret).now()}, headers=headers)

    # دخول بدون رمز — يرجع 428 (يحتاج رمز)
    no_code_response = client.post(
        "/auth/login", json={"email": "needs2fa@example.com", "password": "StrongPass123"}
    )
    assert no_code_response.status_code == 428

    # دخول برمز صحيح — ينجح
    good_response = client.post(
        "/auth/login",
        json={
            "email": "needs2fa@example.com",
            "password": "StrongPass123",
            "totp_code": pyotp.TOTP(secret).now(),
        },
    )
    assert good_response.status_code == 200

    # دخول برمز خاطئ — يرفض
    bad_response = client.post(
        "/auth/login",
        json={
            "email": "needs2fa@example.com",
            "password": "StrongPass123",
            "totp_code": "000000",
        },
    )
    assert bad_response.status_code == 401


def test_disable_two_factor(client):
    token = _register_and_login(client, "disable2fa@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    setup_response = client.post("/auth/2fa/setup", headers=headers)
    secret = setup_response.json()["secret"]
    client.post("/auth/2fa/enable", json={"totp_code": pyotp.TOTP(secret).now()}, headers=headers)

    disable_response = client.post(
        "/auth/2fa/disable", json={"totp_code": pyotp.TOTP(secret).now()}, headers=headers
    )
    assert disable_response.status_code == 200

    # بعد التعطيل، الدخول العادي بدون رمز يشتغل طبيعي
    login_response = client.post(
        "/auth/login", json={"email": "disable2fa@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code == 200


def test_2fa_endpoints_require_authentication(client):
    response = client.post("/auth/2fa/setup")
    assert response.status_code == 401


def test_setup_cannot_replace_secret_while_two_factor_is_enabled(client):
    token = _register_and_login(client, "keep2fa@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    setup = client.post("/auth/2fa/setup", headers=headers)
    original_secret = setup.json()["secret"]
    enabled = client.post(
        "/auth/2fa/enable",
        json={"totp_code": pyotp.TOTP(original_secret).now()},
        headers=headers,
    )
    assert enabled.status_code == 200

    attempted_setup = client.post("/auth/2fa/setup", headers=headers)
    assert attempted_setup.status_code == 409

    # The original factor remains active and can still authenticate the account.
    login = client.post(
        "/auth/login",
        json={
            "email": "keep2fa@example.com",
            "password": "StrongPass123",
            "totp_code": pyotp.TOTP(original_secret).now(),
        },
    )
    assert login.status_code == 200



def test_enable_migrates_legacy_plaintext_secret(client, db_session):
    token = _register_and_login(client, "legacy-enable@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    user = db_session.query(User).filter(User.email == "legacy-enable@example.com").one()
    legacy_secret = pyotp.random_base32()
    user.totp_secret = legacy_secret
    db_session.commit()

    response = client.post(
        "/auth/2fa/enable",
        json={"totp_code": pyotp.TOTP(legacy_secret).now()},
        headers=headers,
    )

    assert response.status_code == 200
    db_session.refresh(user)
    assert user.totp_secret.startswith(TOTP_SECRET_PREFIX)
    assert decrypt_totp_secret(user.totp_secret) == legacy_secret


def test_successful_login_migrates_legacy_plaintext_secret(client, db_session):
    _register_and_login(client, "legacy-login@example.com")
    user = db_session.query(User).filter(User.email == "legacy-login@example.com").one()
    legacy_secret = pyotp.random_base32()
    user.totp_secret = legacy_secret
    user.is_2fa_enabled = True
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "legacy-login@example.com",
            "password": "StrongPass123",
            "totp_code": pyotp.TOTP(legacy_secret).now(),
        },
    )

    assert response.status_code == 200
    db_session.refresh(user)
    assert user.totp_secret.startswith(TOTP_SECRET_PREFIX)
    assert decrypt_totp_secret(user.totp_secret) == legacy_secret



def test_setup_fails_closed_when_encryption_key_is_missing(client, monkeypatch):
    from app.config import settings

    token = _register_and_login(client, "missing-totp-key@example.com")
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", "")

    response = client.post(
        "/auth/2fa/setup",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
