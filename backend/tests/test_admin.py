"""
اختبارات لوحة الإدارة بعد إلغاء منح admin تلقائيًا عند التسجيل العام.
"""
from tests.quiz_helpers import make_admin, take_quiz, topic_id_by_slug, register_and_login


def test_admin_endpoints_reject_regular_user(client):
    token = register_and_login(client, "regular@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/admin/stats", headers=headers).status_code == 403
    assert client.get("/admin/users", headers=headers).status_code == 403
    assert client.get("/admin/analytics/daily", headers=headers).status_code == 403
    assert client.get("/admin/logs", headers=headers).status_code == 403


def test_admin_stats_reflects_activity(client, db_session):
    admin_token = make_admin(client, db_session, "statsadmin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    take_quiz(
        client, db_session, admin_token, topic_id_by_slug(client, "linear-equations"),
        mode="practice", correct=True,
    )
    response = client.get("/admin/stats", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] == 1
    assert body["total_students"] == 0
    assert body["total_teachers"] == 0
    assert body["total_quiz_attempts"] == 1
    assert body["total_lessons"] >= 10
    assert body["total_questions"] >= 50
    assert body["total_assignments"] == 0
    assert "total_conversations" not in body
    assert "total_ai_requests" not in body


def test_admin_can_promote_user_to_teacher(client, db_session):
    admin_token = make_admin(client, db_session, "promoteadmin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    register_and_login(client, "futureteacher@example.com")
    target = next(
        user for user in client.get("/admin/users", headers=admin_headers).json()
        if user["email"] == "futureteacher@example.com"
    )
    assert target["role"] == "user"

    response = client.patch(
        f"/admin/users/{target['id']}", json={"role": "teacher"}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["role"] == "teacher"

    teacher_token = register_and_login(client, "futureteacher@example.com")
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    assert client.post(
        "/assignments", json={"title": "واجب", "description": "وصف"}, headers=teacher_headers
    ).status_code == 201
    assert client.get("/admin/stats", headers=teacher_headers).status_code == 403

    stats = client.get("/admin/stats", headers=admin_headers).json()
    assert stats["total_teachers"] == 1
    assert stats["total_students"] == 0


def test_admin_cannot_change_own_role_or_deactivate_self(client, db_session):
    admin_token = make_admin(client, db_session, "lockout@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    me = client.get("/users/me", headers=admin_headers).json()

    demote = client.patch(
        f"/admin/users/{me['id']}", json={"role": "user"}, headers=admin_headers
    )
    assert demote.status_code == 400
    deactivate = client.patch(
        f"/admin/users/{me['id']}", json={"is_active": False}, headers=admin_headers
    )
    assert deactivate.status_code == 400
    same = client.patch(
        f"/admin/users/{me['id']}", json={"role": "admin"}, headers=admin_headers
    )
    assert same.status_code == 200


def test_admin_can_list_and_update_users(client, db_session):
    admin_token = make_admin(client, db_session, "adminuser@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    register_and_login(client, "targetuser@example.com")

    list_response = client.get("/admin/users", headers=admin_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2
    target = next(user for user in list_response.json() if user["email"] == "targetuser@example.com")

    update_response = client.patch(
        f"/admin/users/{target['id']}", json={"is_active": False}, headers=admin_headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False
    login_response = client.post(
        "/auth/login", json={"email": "targetuser@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code == 401


def test_admin_cannot_delete_own_account_via_admin_route(client, db_session):
    admin_token = make_admin(client, db_session, "selfdelete@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    me = client.get("/users/me", headers=admin_headers).json()
    response = client.delete(f"/admin/users/{me['id']}", headers=admin_headers)
    assert response.status_code == 400


def test_admin_can_delete_other_user(client, db_session):
    admin_token = make_admin(client, db_session, "deleter_admin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    register_and_login(client, "to_delete@example.com")
    users = client.get("/admin/users", headers=admin_headers).json()
    target = next(user for user in users if user["email"] == "to_delete@example.com")

    response = client.delete(f"/admin/users/{target['id']}", headers=admin_headers)
    assert response.status_code == 204
    login_response = client.post(
        "/auth/login", json={"email": "to_delete@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code == 401


def test_admin_logs_capture_key_events(client, db_session):
    admin_token = make_admin(client, db_session, "logsadmin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/admin/logs", headers=admin_headers)
    assert response.status_code == 200
    event_types = [entry["event_type"] for entry in response.json()]
    assert "register" in event_types
    assert "login" in event_types


def test_daily_analytics_includes_today_with_activity(client, db_session):
    admin_token = make_admin(client, db_session, "analyticsadmin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    topic_id = topic_id_by_slug(client, "linear-equations")
    take_quiz(client, db_session, admin_token, topic_id, mode="practice", correct=True)
    take_quiz(client, db_session, admin_token, topic_id, mode="practice", correct=False)

    response = client.get("/admin/analytics/daily?days=7", headers=admin_headers)
    assert response.status_code == 200
    points = response.json()
    assert len(points) == 8
    today = points[-1]
    assert today["new_users"] >= 1
    assert today["quiz_attempts"] == 2
    assert today["average_quiz_score"] == 50.0
    assert today["assignment_submissions"] == 0
    assert "ai_requests" not in today


def test_daily_analytics_requires_admin(client):
    token = register_and_login(client, "nonadmin_analytics@example.com")
    response = client.get(
        "/admin/analytics/daily", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_export_analytics_csv(client, db_session):
    admin_token = make_admin(client, db_session, "csvadmin@example.com")
    response = client.get(
        "/admin/analytics/export.csv", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "date,new_users,quiz_attempts" in response.text
