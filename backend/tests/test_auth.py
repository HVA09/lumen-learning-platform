"""
اختبارات مسارات المصادقة: تسجيل، دخول، وحماية المسارات الخاصة.
التسجيل العام لا يمنح أي مستخدم دور admin، بما في ذلك أول مستخدم.
"""
from app.auth.security import create_password_reset_token
from app.models.user import User


def test_register_new_user(client):
    response = client.post(
        "/auth/register", json={"email": "test@example.com", "password": "StrongPass123"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "test@example.com"
    assert body["role"] == "user"
    assert "hashed_password" not in body


def test_register_duplicate_email_fails(client):
    client.post("/auth/register", json={"email": "dup@example.com", "password": "StrongPass123"})
    response = client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "AnotherPass123"}
    )
    assert response.status_code == 400


def test_register_rejects_short_password(client):
    response = client.post(
        "/auth/register", json={"email": "short@example.com", "password": "1234567"}
    )
    assert response.status_code == 422


def test_registration_rejects_passwords_over_bcrypt_byte_limit(client):
    # 73 ASCII bytes, and 74 UTF-8 bytes respectively.
    for email, password in (
        ("long-password-ascii@example.com", "x" * 73),
        ("long-password-unicode@example.com", "ا" * 37),
    ):
        response = client.post(
            "/auth/register", json={"email": email, "password": password}
        )
        assert response.status_code == 422


def test_first_user_does_not_become_admin(client):
    response = client.post(
        "/auth/register", json={"email": "first@example.com", "password": "StrongPass123"}
    )
    assert response.json()["role"] == "user"


def test_second_user_is_regular(client):
    client.post("/auth/register", json={"email": "first@example.com", "password": "StrongPass123"})
    response = client.post(
        "/auth/register", json={"email": "second@example.com", "password": "StrongPass123"}
    )
    assert response.json()["role"] == "user"


def test_login_success_returns_tokens(client):
    client.post(
        "/auth/register", json={"email": "login@example.com", "password": "StrongPass123"}
    )
    response = client.post(
        "/auth/login", json={"email": "login@example.com", "password": "StrongPass123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_wrong_password_fails(client):
    client.post(
        "/auth/register", json={"email": "wrong@example.com", "password": "StrongPass123"}
    )
    response = client.post(
        "/auth/login", json={"email": "wrong@example.com", "password": "WrongPassword"}
    )
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_refresh_fails_for_deactivated_user(client, db_session):
    client.post(
        "/auth/register", json={"email": "inactive@example.com", "password": "StrongPass123"}
    )
    login_response = client.post(
        "/auth/login", json={"email": "inactive@example.com", "password": "StrongPass123"}
    )
    refresh_token = login_response.json()["refresh_token"]

    user = db_session.query(User).filter(User.email == "inactive@example.com").first()
    user.is_active = False
    db_session.commit()

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


def test_password_change_revokes_existing_access_and_refresh_tokens(client):
    email = "password-change-revoke@example.com"
    client.post("/auth/register", json={"email": email, "password": "OldPassword123"})
    login = client.post("/auth/login", json={"email": email, "password": "OldPassword123"})
    assert login.status_code == 200
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    changed = client.post(
        "/users/me/change-password",
        json={"current_password": "OldPassword123", "new_password": "NewPassword456"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert client.get("/users/me", headers=headers).status_code == 401
    assert client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).status_code == 401

    new_login = client.post(
        "/auth/login", json={"email": email, "password": "NewPassword456"}
    )
    assert new_login.status_code == 200


def test_password_reset_token_is_single_use_and_revokes_sessions(client, db_session):
    email = "password-reset-revoke@example.com"
    client.post("/auth/register", json={"email": email, "password": "OldPassword123"})
    login = client.post("/auth/login", json={"email": email, "password": "OldPassword123"})
    assert login.status_code == 200
    tokens = login.json()
    user = db_session.query(User).filter(User.email == email).one()
    reset_token = create_password_reset_token(user.id, user.token_version)

    reset = client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "ResetPassword789"},
    )
    assert reset.status_code == 200

    # A redeemed token cannot be replayed, even before its JWT expiry.
    replay = client.post(
        "/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "AnotherPassword999"},
    )
    assert replay.status_code == 400

    assert client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    ).status_code == 401
    assert client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).status_code == 401
    assert client.post(
        "/auth/login", json={"email": email, "password": "ResetPassword789"}
    ).status_code == 200


def test_registration_rejects_extremely_long_password(client):
    response = client.post(
        "/auth/register",
        json={"email": "extremely-long-password@example.com", "password": "x" * 10000},
    )
    assert response.status_code == 422
