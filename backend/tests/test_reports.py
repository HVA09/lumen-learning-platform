"""
اختبارات تقرير التقدّم: بناء التقرير نفسه + مسارات العرض والإرسال الفوري
"""
from app.models.topic_mastery import TopicMastery
from app.models.user import User
from tests.quiz_helpers import make_student, take_quiz, topic_id_by_slug

def _register_and_login(client, email="reportuser@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.cookies.get("lumen_access")


def test_progress_report_reflects_zero_activity_for_new_user(client):
    token = _register_and_login(client, "newreportuser@example.com")
    response = client.get(
        "/reports/my-progress", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["topics_practiced"] == 0
    assert body["average_mastery"] == 0
    assert body["weak_topics"] == []


def test_progress_report_reflects_mastery_and_weak_topics(client, db_session):
    token = _register_and_login(client, "activereportuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    user = db_session.query(User).filter(User.email == "activereportuser@example.com").first()
    linear_id = topic_id_by_slug(client, "linear-equations")
    projectile_id = topic_id_by_slug(client, "projectile-motion")
    # الإتقان يُحسب بالسيرفر من الاختبارات فقط (ما فيه مسار يكتبه)، فنجهّز الحالة مباشرة بقاعدة البيانات
    db_session.add(TopicMastery(user_id=user.id, topic_id=linear_id, mastery_percentage=30.0,
                                gateway_quiz_passed=False, attempts_count=1))
    db_session.add(TopicMastery(user_id=user.id, topic_id=projectile_id, mastery_percentage=90.0,
                                gateway_quiz_passed=True, attempts_count=2))
    db_session.commit()

    response = client.get("/reports/my-progress", headers=headers)
    body = response.json()
    assert body["topics_practiced"] == 2
    assert body["gateway_quizzes_passed"] == 1
    assert "المعادلات الخطية" in body["weak_topics"]  # إتقان 30% تحت العتبة


def test_progress_report_includes_quiz_lesson_and_streak_stats(client, db_session):
    token = make_student(client, "quizreportuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    topic_id = topic_id_by_slug(client, "linear-equations")
    take_quiz(client, db_session, token, topic_id, mode="practice", correct=True)
    take_quiz(client, db_session, token, topic_id, mode="practice", correct=False)

    lessons = client.get(f"/curriculum/topics/{topic_id}/lessons", headers=headers).json()
    client.post(f"/curriculum/lessons/{lessons[0]['id']}/complete", headers=headers)

    body = client.get("/reports/my-progress", headers=headers).json()
    assert body["quizzes_taken"] == 2
    assert body["average_quiz_score"] == 50.0
    assert body["lessons_completed"] == 1
    assert body["streak_days"] == 1
    assert body["average_mastery"] == 50.0


def test_progress_report_counts_due_cards_and_leeches(client):
    token = _register_and_login(client, "cardreportuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/srs/cards", json={"front_text": "س", "back_text": "ج"}, headers=headers)

    response = client.get("/reports/my-progress", headers=headers)
    assert response.json()["cards_due_now"] == 1


def test_send_my_report_succeeds_even_without_real_smtp(client):
    # بدون SMTP_HOST مضبوط، الإرسال يطبع باللوق بدل الفشل — الطلب لازم ينجح برضو
    token = _register_and_login(client, "sendreportuser@example.com")
    response = client.post(
        "/reports/send-my-report", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "تم إرسال" in response.json()["detail"]


def test_reports_require_authentication(client):
    assert client.get("/reports/my-progress").status_code == 401
    assert client.post("/reports/send-my-report").status_code == 401
