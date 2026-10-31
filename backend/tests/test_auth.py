"""
اختبارات مسارات المصادقة: تسجيل، دخول، وحماية المسارات الخاصة.
التسجيل العام لا يمنح أي مستخدم دور admin، بما في ذلك أول مستخدم.
"""
from app.auth.security import create_password_reset_token
from app.config import settings
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
    assert body["authenticated"] is True
    assert "access_token" not in body
    assert "refresh_token" not in body
    assert response.cookies.get("lumen_access")
    assert response.cookies.get("lumen_refresh")
    assert "httponly" in response.headers.get("set-cookie", "").lower()


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

    user = db_session.query(User).filter(User.email == "inactive@example.com").first()
    user.is_active = False
    db_session.commit()

    response = client.post("/auth/refresh", headers={"X-CSRF-Token": client.cookies.get("lumen_csrf")})
    assert response.status_code == 401


def test_password_change_revokes_existing_access_and_refresh_tokens(client):
    email = "password-change-revoke@example.com"
    client.post("/auth/register", json={"email": email, "password": "OldPassword123"})
    login = client.post("/auth/login", json={"email": email, "password": "OldPassword123"})
    assert login.status_code == 200
    tokens = login.cookies
    headers = {"Authorization": f"Bearer {tokens.get('lumen_access')}"}

    changed = client.post(
        "/users/me/change-password",
        json={"current_password": "OldPassword123", "new_password": "NewPassword456"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert client.get("/users/me", headers=headers).status_code == 401
    assert client.post(
        "/auth/refresh", headers={"X-CSRF-Token": client.cookies.get("lumen_csrf")}
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
    tokens = login.cookies
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
        headers={"Authorization": f"Bearer {tokens.get('lumen_access')}"},
    ).status_code == 401
    assert client.post(
        "/auth/refresh",
        headers={"X-CSRF-Token": client.cookies.get("lumen_csrf")},
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


def test_registration_accepts_password_at_bcrypt_byte_limit(client):
    response = client.post(
        "/auth/register",
        json={"email": "maximum-password@example.com", "password": "x" * 72},
    )
    assert response.status_code == 201

def test_csrf_bootstrap_sets_cookie_and_returns_matching_token(client):
    response = client.get("/auth/csrf")
    assert response.status_code == 200
    assert response.json()["csrf_token"] == response.cookies.get("lumen_csrf")


def test_cookie_authenticated_mutations_require_valid_csrf_token(client):
    client.post(
        "/auth/register",
        json={"email": "csrf-cookie@example.com", "password": "StrongPass123"},
    )
    login = client.post(
        "/auth/login",
        json={"email": "csrf-cookie@example.com", "password": "StrongPass123"},
    )
    assert login.status_code == 200

    assert client.get("/users/me").status_code == 200
    rejected = client.patch("/users/me", json={"full_name": "بدون CSRF"})
    assert rejected.status_code == 403

    csrf_token = client.cookies.get("lumen_csrf")
    accepted = client.patch(
        "/users/me",
        json={"full_name": "مع CSRF"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert accepted.status_code == 200
    assert accepted.json()["full_name"] == "مع CSRF"


def test_logout_revokes_cookie_session_and_clears_session_cookies(client):
    client.post(
        "/auth/register",
        json={"email": "logout-cookie@example.com", "password": "StrongPass123"},
    )
    login = client.post(
        "/auth/login",
        json={"email": "logout-cookie@example.com", "password": "StrongPass123"},
    )
    assert login.status_code == 200
    assert client.get("/users/me").status_code == 200

    response = client.post(
        "/auth/logout",
        headers={"X-CSRF-Token": client.cookies.get("lumen_csrf")},
    )
    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    assert client.cookies.get("lumen_access") is None
    assert client.cookies.get("lumen_refresh") is None
    assert client.get("/users/me").status_code == 401

def test_browser_login_requires_trusted_origin_and_csrf_header(client):
    email = "browser-login-csrf@example.com"
    client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    origin = settings.CORS_ORIGINS[0]

    missing_csrf = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
        headers={"origin": origin},
    )
    assert missing_csrf.status_code == 403

    csrf_response = client.get("/auth/csrf")
    csrf_token = csrf_response.json()["csrf_token"]
    untrusted_origin = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
        headers={
            "origin": "https://attacker.invalid",
            "X-CSRF-Token": csrf_token,
        },
    )
    assert untrusted_origin.status_code == 403

    accepted = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
        headers={"origin": origin, "X-CSRF-Token": csrf_token},
    )
    assert accepted.status_code == 200
    assert accepted.json()["authenticated"] is True


def test_refresh_rotates_cookie_tokens_and_csrf_token(client):
    client.post(
        "/auth/register",
        json={"email": "refresh-cookie@example.com", "password": "StrongPass123"},
    )
    login = client.post(
        "/auth/login",
        json={"email": "refresh-cookie@example.com", "password": "StrongPass123"},
    )
    old_access = login.cookies.get("lumen_access")
    old_refresh = login.cookies.get("lumen_refresh")
    old_csrf = login.cookies.get("lumen_csrf")

    rejected = client.post("/auth/refresh")
    assert rejected.status_code == 403

    refreshed = client.post(
        "/auth/refresh",
        headers={"X-CSRF-Token": old_csrf},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["authenticated"] is True
    assert client.cookies.get("lumen_access") != old_access
    assert client.cookies.get("lumen_refresh") != old_refresh
    assert client.cookies.get("lumen_csrf") == refreshed.json()["csrf_token"]
