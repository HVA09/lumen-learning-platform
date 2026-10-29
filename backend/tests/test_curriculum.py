"""
اختبارات طبقة المنهج (Lumen): المواد والمواضيع، الإتقان (يُقرأ فقط)، مسار الطالب، والدروس
"""
from tests.quiz_helpers import auth, make_student, take_quiz, topic_id_by_slug


def test_list_subjects_is_public_and_seeded(client):
    response = client.get("/curriculum/subjects")
    assert response.status_code == 200
    slugs = [s["slug"] for s in response.json()]
    assert "math" in slugs
    assert "physics" in slugs
    assert "programming" in slugs


def test_subjects_include_nested_topics(client):
    response = client.get("/curriculum/subjects")
    math_subject = next(s for s in response.json() if s["slug"] == "math")
    topic_slugs = [t["slug"] for t in math_subject["topics"]]
    assert "linear-equations" in topic_slugs


def test_get_topic_detail(client):
    topic_id = topic_id_by_slug(client, "linear-equations")
    response = client.get(f"/curriculum/topics/{topic_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "linear-equations"
    assert len(body["learning_outcomes_ar"]) >= 1


def test_get_topic_not_found(client):
    response = client.get("/curriculum/topics/999999")
    assert response.status_code == 404


def test_mastery_defaults_to_zero_before_any_attempt(client):
    token = make_student(client, "newstudent@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    response = client.get(f"/curriculum/topics/{topic_id}/mastery", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["mastery_percentage"] == 0.0
    assert response.json()["gateway_quiz_passed"] is False


def test_client_can_no_longer_set_mastery_directly(client):
    # الإتقان يُحسب بالسيرفر من نتائج الاختبارات — ما فيه مسار PUT يقبل نسبة جاهزة من المتصفح
    token = make_student(client, "cheater@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    response = client.put(
        f"/curriculum/topics/{topic_id}/mastery",
        json={"mastery_percentage": 100, "gateway_quiz_passed": True},
        headers=auth(token),
    )
    assert response.status_code == 405
    mastery = client.get(f"/curriculum/topics/{topic_id}/mastery", headers=auth(token)).json()
    assert mastery["mastery_percentage"] == 0.0
    assert mastery["gateway_quiz_passed"] is False


def test_mastery_requires_authentication(client):
    topic_id = topic_id_by_slug(client, "linear-equations")
    assert client.get(f"/curriculum/topics/{topic_id}/mastery").status_code == 401


# ---------- مسار التعلّم ----------

def _path_topics(client, token):
    body = client.get("/curriculum/path", headers=auth(token)).json()
    return body, {t["slug"]: t for s in body["subjects"] for t in s["topics"]}


def test_learning_path_requires_authentication(client):
    assert client.get("/curriculum/path").status_code == 401


def test_new_student_path_locks_topics_with_prerequisites(client):
    token = make_student(client, "pathnew@example.com")
    body, topics = _path_topics(client, token)

    assert topics["linear-equations"]["status"] == "available"
    assert topics["derivatives-intro"]["status"] == "locked"
    assert topics["derivatives-intro"]["prerequisite_name_ar"] == "المعادلات الخطية"
    assert topics["projectile-motion"]["status"] == "available"
    assert body["topics_mastered"] == 0
    assert body["topics_total"] >= 5
    assert body["recommended_topic_id"] == topics["linear-equations"]["id"]
    assert topics["linear-equations"]["lessons_total"] == 2
    assert topics["linear-equations"]["questions_count"] >= 10


def test_passing_gateway_unlocks_dependent_topic_in_path(client, db_session):
    token = make_student(client, "pathpass@example.com")
    linear_id = topic_id_by_slug(client, "linear-equations")

    result = take_quiz(client, db_session, token, linear_id, mode="gateway", correct=True)
    assert result["passed"] is True

    body, topics = _path_topics(client, token)
    assert topics["linear-equations"]["status"] == "mastered"
    assert topics["linear-equations"]["mastery_percentage"] == 100.0
    assert topics["derivatives-intro"]["status"] == "available"
    assert body["topics_mastered"] == 1
    assert body["recommended_topic_id"] == topics["derivatives-intro"]["id"]


# ---------- الدروس ----------

def test_topic_lessons_require_authentication(client):
    topic_id = topic_id_by_slug(client, "linear-equations")
    assert client.get(f"/curriculum/topics/{topic_id}/lessons").status_code == 401


def test_topic_lessons_are_seeded_in_order_and_start_incomplete(client):
    token = make_student(client, "reader@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")

    response = client.get(f"/curriculum/topics/{topic_id}/lessons", headers=auth(token))
    assert response.status_code == 200
    lessons = response.json()
    assert len(lessons) == 2
    assert [l["order_index"] for l in lessons] == sorted(l["order_index"] for l in lessons)
    assert all(l["completed"] is False for l in lessons)
    assert all(len(l["body_md"]) > 100 for l in lessons)


def test_lessons_for_unknown_topic_404(client):
    token = make_student(client, "reader404@example.com")
    assert client.get("/curriculum/topics/999999/lessons", headers=auth(token)).status_code == 404


def test_complete_lesson_is_idempotent_and_updates_progress(client):
    token = make_student(client, "finisher@example.com")
    headers = auth(token)
    topic_id = topic_id_by_slug(client, "linear-equations")
    lessons = client.get(f"/curriculum/topics/{topic_id}/lessons", headers=headers).json()

    first = client.post(f"/curriculum/lessons/{lessons[0]['id']}/complete", headers=headers)
    assert first.status_code == 200
    assert first.json()["completed"] is True
    assert any(a["key"] == "first_lesson" for a in first.json()["new_achievements"])

    again = client.post(f"/curriculum/lessons/{lessons[0]['id']}/complete", headers=headers)
    assert again.status_code == 200
    assert again.json()["new_achievements"] == []  # ما يتكرر فتح الإنجاز

    refreshed = client.get(f"/curriculum/topics/{topic_id}/lessons", headers=headers).json()
    assert [l["completed"] for l in refreshed] == [True, False]

    _, topics = _path_topics(client, token)
    assert topics["linear-equations"]["lessons_completed"] == 1
    assert topics["linear-equations"]["status"] == "in_progress"


def test_complete_unknown_lesson_404(client):
    token = make_student(client, "finisher404@example.com")
    assert client.post("/curriculum/lessons/999999/complete", headers=auth(token)).status_code == 404


def test_complete_lesson_requires_authentication(client):
    assert client.post("/curriculum/lessons/1/complete").status_code == 401

