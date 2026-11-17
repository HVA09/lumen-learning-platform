"""اختبارات المرحلة الرابعة: الملف الشخصي، تغيير كلمة المرور، حذف الحساب."""

from app.models.user import User, UserRole
from app.routers import users as users_router


def _register_and_login(client, email="profile@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.cookies.get("lumen_access")


def test_get_me_includes_profile_fields(client):
    token = _register_and_login(client)
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    body = response.json()
    assert body["full_name"] is None
    assert body["avatar_url"] is None
    assert body["is_2fa_enabled"] is False


def test_update_profile(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch(
        "/users/me",
        json={"full_name": "محمد", "avatar_url": "https://example.com/avatar.png"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "محمد"
    assert body["avatar_url"] == "https://example.com/avatar.png"


def test_update_profile_partial_leaves_other_field_untouched(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.patch("/users/me", json={"full_name": "محمد"}, headers=headers)

    response = client.patch(
        "/users/me", json={"avatar_url": "https://example.com/a.png"}, headers=headers
    )
    assert response.json()["full_name"] == "محمد"
    assert response.json()["avatar_url"] == "https://example.com/a.png"


def test_change_password_requires_correct_current_password(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/users/me/change-password",
        json={"current_password": "WrongOne123", "new_password": "NewPass123"},
        headers=headers,
    )
    assert response.status_code == 401


def test_change_password_success_allows_login_with_new_password(client):
    token = _register_and_login(client, "changepw@example.com", "OldPass123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/users/me/change-password",
        json={"current_password": "OldPass123", "new_password": "NewPass123"},
        headers=headers,
    )
    assert response.status_code == 200

    old_login = client.post(
        "/auth/login", json={"email": "changepw@example.com", "password": "OldPass123"}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login", json={"email": "changepw@example.com", "password": "NewPass123"}
    )
    assert new_login.status_code == 200


def test_delete_account_requires_correct_password(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.request(
        "DELETE", "/users/me", json={"password": "WrongPassword"}, headers=headers
    )
    assert response.status_code == 401


def test_delete_account_success(client):
    token = _register_and_login(client, "deleteme@example.com", "StrongPass123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.request(
        "DELETE", "/users/me", json={"password": "StrongPass123"}, headers=headers
    )
    assert response.status_code == 204

    login_response = client.post(
        "/auth/login", json={"email": "deleteme@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code == 401


def test_last_active_admin_cannot_delete_own_account(client, db_session):
    password = _register_and_login.__defaults__[1]
    token = _register_and_login(client, "last-admin@example.com", password)
    admin = db_session.query(User).filter(User.email == "last-admin@example.com").one()
    admin.role = UserRole.admin
    db_session.commit()
    headers = {"Authorization": f"Bearer {token}"}

    response = client.request(
        "DELETE", "/users/me", json={"password": password}, headers=headers
    )

    assert response.status_code == 409
    assert db_session.query(User.id).filter(User.id == admin.id).one()[0] == admin.id
    assert client.get("/admin/stats", headers=headers).status_code == 200


def test_admin_can_delete_own_account_when_another_active_admin_remains(client, db_session):
    password = _register_and_login.__defaults__[1]
    first_token = _register_and_login(client, "first-admin-delete@example.com", password)
    second_token = _register_and_login(client, "second-admin-delete@example.com", password)
    first_admin = db_session.query(User).filter(User.email == "first-admin-delete@example.com").one()
    second_admin = db_session.query(User).filter(User.email == "second-admin-delete@example.com").one()
    first_admin.role = UserRole.admin
    second_admin.role = UserRole.admin
    db_session.commit()

    response = client.request(
        "DELETE",
        "/users/me",
        json={"password": password},
        headers={"Authorization": f"Bearer {first_token}"},
    )

    assert response.status_code == 204
    assert db_session.query(User.id).filter(User.id == first_admin.id).count() == 0
    assert client.get(
        "/admin/stats", headers={"Authorization": f"Bearer {second_token}"}
    ).status_code == 200


def test_self_delete_rechecks_admin_promotion_after_roster_lock(client, db_session, monkeypatch):
    password = _register_and_login.__defaults__[1]
    token = _register_and_login(client, "racing_self_delete@example.com", password)
    current_user = db_session.query(User).filter(User.email == "racing_self_delete@example.com").one()
    _register_and_login(client, "concurrent_admin@example.com", password)
    existing_admin = db_session.query(User).filter(User.email == "concurrent_admin@example.com").one()
    existing_admin.role = UserRole.admin
    db_session.commit()
    original_lock = users_router.lock_active_admin_ids

    def concurrent_change(db):
        # Simulate a concurrent promotion of this account plus removal of the
        # previous admin after authentication but before the self-delete read.
        db.query(User).filter(User.id == current_user.id).update(
            {User.role: UserRole.admin}, synchronize_session=False
        )
        db.query(User).filter(User.id == existing_admin.id).update(
            {User.role: UserRole.user}, synchronize_session=False
        )
        db.commit()
        return original_lock(db)

    monkeypatch.setattr(users_router, "lock_active_admin_ids", concurrent_change)
    response = client.request(
        "DELETE",
        "/users/me",
        json={"password": password},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409
    assert db_session.query(User).filter(User.id == current_user.id).one().role == UserRole.admin
    assert db_session.query(User).filter(User.id == current_user.id).one().is_active is True


def test_profile_endpoints_require_authentication(client):
    assert client.patch("/users/me", json={"full_name": "x"}).status_code == 401
    assert (
        client.post(
            "/users/me/change-password",
            json={"current_password": "a", "new_password": "bbbbbbbb"},
        ).status_code
        == 401
    )
