"""
اختبارات مسارات المصادقة: تسجيل، دخول، وحماية المسارات الخاصة.
التسجيل العام لا يمنح أي مستخدم دور admin، بما في ذلك أول مستخدم.
"""
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
