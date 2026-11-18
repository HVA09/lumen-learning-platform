"""
اختبارات إدارة المحتوى (معلّم/admin): الدروس وبنك الأسئلة — والطالب ممنوع
"""
from app.models.question import Question
from app.models.lesson import Lesson
from app.models.question_result import QuestionResult
from app.models.user import UserRole
from tests.quiz_helpers import (
    auth,
    make_student,
    make_teacher,
    register_and_login,
    set_role,
    take_quiz,
    topic_id_by_slug,
)

VALID_MCQ = {
    "kind": "mcq",
    "prompt_ar": "كم ناتج `2 + 2`؟",
    "choices": ["3", "4", "5"],
    "correct_answer": 1,
    "explanation_ar": "2 + 2 = 4",
    "difficulty": 1,
}


def test_content_endpoints_require_authentication(client):
    topic_id = topic_id_by_slug(client, "linear-equations")
    assert client.get(f"/content/topics/{topic_id}/questions").status_code == 401
    assert client.post(f"/content/topics/{topic_id}/questions", json=VALID_MCQ).status_code == 401


def test_student_cannot_read_or_manage_questions(client):
    token = make_student(client, "curious@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    assert client.get(f"/content/topics/{topic_id}/questions", headers=auth(token)).status_code == 403
    assert (
        client.post(f"/content/topics/{topic_id}/questions", json=VALID_MCQ, headers=auth(token)).status_code
        == 403
    )
    assert (
        client.post(
            f"/content/topics/{topic_id}/lessons",
            json={"title_ar": "س", "body_md": "نص"},
            headers=auth(token),
        ).status_code
        == 403
    )


def test_teacher_lists_seeded_questions_with_answers(client, db_session):
    token = make_teacher(client, db_session)
    topic_id = topic_id_by_slug(client, "linear-equations")

    response = client.get(f"/content/topics/{topic_id}/questions", headers=auth(token))
    assert response.status_code == 200
    questions = response.json()
    assert len(questions) >= 10
    assert all("correct_answer" in q for q in questions)


def test_teacher_can_create_update_and_delete_a_question(client, db_session):
    token = make_teacher(client, db_session)
    headers = auth(token)
    topic_id = topic_id_by_slug(client, "linear-equations")

    created = client.post(f"/content/topics/{topic_id}/questions", json=VALID_MCQ, headers=headers)
    assert created.status_code == 201
    question = created.json()
    assert question["correct_answer"] == 1
    assert question["topic_id"] == topic_id
    assert question["is_active"] is True

    updated_payload = {**VALID_MCQ, "correct_answer": 2, "prompt_ar": "سؤال معدّل"}
    updated = client.put(f"/content/questions/{question['id']}", json=updated_payload, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["correct_answer"] == 2
    assert updated.json()["prompt_ar"] == "سؤال معدّل"

    assert client.delete(f"/content/questions/{question['id']}", headers=headers).status_code == 204
    listed = client.get(f"/content/topics/{topic_id}/questions", headers=headers).json()
    assert all(q["id"] != question["id"] for q in listed)
    assert client.delete(f"/content/questions/{question['id']}", headers=headers).status_code == 404


def test_question_validation_rejects_bad_definitions(client, db_session):
    token = make_teacher(client, db_session)
    headers = auth(token)
    topic_id = topic_id_by_slug(client, "linear-equations")
    url = f"/content/topics/{topic_id}/questions"

    bad_payloads = [
        {**VALID_MCQ, "correct_answer": 7},  # رقم خارج الخيارات
        {**VALID_MCQ, "choices": ["فقط خيار واحد"], "correct_answer": 0},
        {**VALID_MCQ, "kind": "essay"},
        {"kind": "numeric", "prompt_ar": "س؟", "correct_answer": "ليس رقمًا"},
        {"kind": "true_false", "prompt_ar": "س؟", "correct_answer": "نعم"},
        {"kind": "short_text", "prompt_ar": "س؟", "correct_answer": []},
        {**VALID_MCQ, "prompt_ar": ""},
        {**VALID_MCQ, "difficulty": 9},
    ]
    for payload in bad_payloads:
        assert client.post(url, json=payload, headers=headers).status_code == 422, payload


def test_numeric_question_is_normalized_and_graded_with_tolerance(client, db_session):
    token = make_teacher(client, db_session)
    headers = auth(token)
    topic_id = topic_id_by_slug(client, "linear-equations")

    created = client.post(
        f"/content/topics/{topic_id}/questions",
        json={"kind": "numeric", "prompt_ar": "قرّب π لأقرب جزء من مئة", "correct_answer": "3.14", "tolerance": 0.01},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["correct_answer"] == 3.14
    assert created.json()["choices"] is None


def test_question_for_unknown_topic_404(client, db_session):
    token = make_teacher(client, db_session)
    response = client.post("/content/topics/999999/questions", json=VALID_MCQ, headers=auth(token))
    assert response.status_code == 404


def test_admin_can_manage_content_too(client, db_session):
    admin_token = register_and_login(client, "contentadmin@example.com")
    set_role(db_session, "contentadmin@example.com", UserRole.admin)
    topic_id = topic_id_by_slug(client, "linear-equations")
    response = client.post(
        f"/content/topics/{topic_id}/questions", json=VALID_MCQ, headers=auth(admin_token)
    )
    assert response.status_code == 201


def test_teacher_lesson_lifecycle_and_unpublished_lessons_are_hidden_from_students(client, db_session):
    teacher_token = make_teacher(client, db_session)
    student_token = make_student(client, "lessonstudent@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    url = f"/content/topics/{topic_id}/lessons"

    created = client.post(
        url,
        json={"title_ar": "درس جديد", "body_md": "## عنوان\n\nنص الدرس", "estimated_minutes": 4, "order_index": 5, "is_published": False},
        headers=auth(teacher_token),
    )
    assert created.status_code == 201
    lesson = created.json()
    assert lesson["slug"].startswith("lesson-")
    assert lesson["is_published"] is False

    # مخفي عن الطالب طالما غير منشور
    student_view = client.get(f"/curriculum/topics/{topic_id}/lessons", headers=auth(student_token)).json()
    assert all(visible_lesson["id"] != lesson["id"] for visible_lesson in student_view)
    assert client.post(f"/curriculum/lessons/{lesson['id']}/complete", headers=auth(student_token)).status_code == 404

    # المعلّم يشوفه ويعدّله وينشره
    teacher_view = client.get(url, headers=auth(teacher_token)).json()
    assert any(visible_lesson["id"] == lesson["id"] for visible_lesson in teacher_view)
    updated = client.put(
        f"/content/lessons/{lesson['id']}",
        json={"title_ar": "درس منشور", "body_md": "نص", "estimated_minutes": 4, "order_index": 5, "is_published": True},
        headers=auth(teacher_token),
    )
    assert updated.status_code == 200
    student_view = client.get(f"/curriculum/topics/{topic_id}/lessons", headers=auth(student_token)).json()
    assert any(visible_lesson["id"] == lesson["id"] and visible_lesson["title_ar"] == "درس منشور" for visible_lesson in student_view)

    assert client.delete(f"/content/lessons/{lesson['id']}", headers=auth(teacher_token)).status_code == 204
    assert client.delete(f"/content/lessons/{lesson['id']}", headers=auth(teacher_token)).status_code == 404


# ---------- تحليل الأسئلة ----------

def _add_results(db_session, attempt_id, question, outcomes):
    """يضيف نتائج جاهزة لسؤال: outcomes قائمة (correct, given_answer)"""
    for correct, given in outcomes:
        db_session.add(
            QuestionResult(quiz_attempt_id=attempt_id, question_id=question.id, correct=correct, given_answer=given)
        )
    db_session.commit()


def test_analytics_requires_teacher(client):
    topic_id = topic_id_by_slug(client, "linear-equations")
    assert client.get(f"/content/topics/{topic_id}/analytics").status_code == 401
    student = make_student(client, "analytics-student@example.com")
    assert client.get(f"/content/topics/{topic_id}/analytics", headers=auth(student)).status_code == 403


def test_analytics_for_unknown_topic_404(client, db_session):
    teacher = make_teacher(client, db_session)
    assert client.get("/content/topics/999999/analytics", headers=auth(teacher)).status_code == 404


def test_analytics_without_any_attempts_is_all_insufficient_data(client, db_session):
    teacher = make_teacher(client, db_session)
    topic_id = topic_id_by_slug(client, "linear-equations")
    rows = client.get(f"/content/topics/{topic_id}/analytics", headers=auth(teacher)).json()
    assert len(rows) >= 10
    assert all(r["flag"] == "insufficient_data" and r["answered"] == 0 for r in rows)
    assert all(r["success_rate"] is None for r in rows)


def test_quiz_submission_records_one_result_per_question(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "recorded@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    result = take_quiz(client, db_session, student, topic_id, mode="practice", correct=True)

    stored = db_session.query(QuestionResult).filter(QuestionResult.quiz_attempt_id == result["attempt_id"]).all()
    assert len(stored) == 5
    assert all(r.correct for r in stored)

    rows = client.get(f"/content/topics/{topic_id}/analytics", headers=auth(teacher)).json()
    assert sum(r["answered"] for r in rows) == 5
    assert sum(r["correct"] for r in rows) == 5


def test_analytics_flags_question_nobody_answers_correctly(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "attempter@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = take_quiz(client, db_session, student, topic_id, mode="practice", correct=True)
    question = db_session.query(Question).filter(Question.key == "lin-01").first()
    db_session.query(QuestionResult).delete()  # نبدأ من صفر لنتحكم بالبيانات
    _add_results(db_session, attempt["attempt_id"], question, [(False, 2)] * 4 + [(False, "0")] * 2)

    rows = client.get(f"/content/topics/{topic_id}/analytics", headers=auth(teacher)).json()
    row = next(r for r in rows if r["question_id"] == question.id)
    assert row["answered"] == 6
    assert row["correct"] == 0
    assert row["success_rate"] == 0.0
    assert row["flag"] == "check_answer_key"
    assert row["top_wrong_answer"] == question.choices[2]  # الخيار 2 اختاره 4 طلاب
    assert row["top_wrong_count"] == 4


def test_analytics_sorts_weakest_first_and_puts_unanswered_last(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "sorter@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = take_quiz(client, db_session, student, topic_id, mode="practice", correct=True)
    db_session.query(QuestionResult).delete()

    weak = db_session.query(Question).filter(Question.key == "lin-05").first()
    strong = db_session.query(Question).filter(Question.key == "lin-06").first()  # صعوبة 2 (نطاق 40–90%)
    _add_results(db_session, attempt["attempt_id"], weak, [(True, 1)] + [(False, 0)] * 4)  # 20%
    _add_results(db_session, attempt["attempt_id"], strong, [(True, 7)] * 5)  # 100%

    rows = client.get(f"/content/topics/{topic_id}/analytics", headers=auth(teacher)).json()
    ids = [r["question_id"] for r in rows]
    assert ids[0] == weak.id
    assert ids[1] == strong.id
    assert all(r["flag"] == "insufficient_data" for r in rows[2:])
    assert rows[0]["flag"] == "harder_than_declared"
    assert rows[1]["flag"] == "easier_than_declared"  # 100% > 90% لسؤال مصنّف متوسط


def test_true_false_top_wrong_answer_is_labelled(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "tf-attempter@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = take_quiz(client, db_session, student, topic_id, mode="practice", correct=True)
    db_session.query(QuestionResult).delete()
    question = db_session.query(Question).filter(Question.key == "lin-04").first()  # صح/خطأ، الصحيح False
    _add_results(db_session, attempt["attempt_id"], question, [(False, True)] * 3 + [(True, False)] * 3)

    row = next(
        r for r in client.get(f"/content/topics/{topic_id}/analytics", headers=auth(teacher)).json()
        if r["question_id"] == question.id
    )
    assert row["top_wrong_answer"] == "صحيح"
    assert row["top_wrong_count"] == 3
    assert row["success_rate"] == 50.0



def test_questions_are_shared_read_only_and_managed_by_creator_or_admin(client, db_session):
    owner = make_teacher(client, db_session, "question-owner@example.com")
    other = make_teacher(client, db_session, "question-other@example.com")
    admin = register_and_login(client, "question-admin@example.com")
    set_role(db_session, "question-admin@example.com", UserRole.admin)
    topic_id = topic_id_by_slug(client, "linear-equations")
    headers_owner, headers_other, headers_admin = auth(owner), auth(other), auth(admin)

    created = client.post(
        f"/content/topics/{topic_id}/questions", json=VALID_MCQ, headers=headers_owner
    )
    assert created.status_code == 201
    question_id = created.json()["id"]

    # Other teachers can read the shared curriculum, but cannot mutate another teacher's question.
    listed = client.get(f"/content/topics/{topic_id}/questions", headers=headers_other)
    assert listed.status_code == 200
    assert question_id in {question["id"] for question in listed.json()}
    payload = {**VALID_MCQ, "prompt_ar": "تعديل غير مصرح"}
    assert client.put(
        f"/content/questions/{question_id}", json=payload, headers=headers_other
    ).status_code == 403
    assert client.delete(
        f"/content/questions/{question_id}", headers=headers_other
    ).status_code == 403

    # The author and an admin may manage the question.
    assert client.put(
        f"/content/questions/{question_id}",
        json={**VALID_MCQ, "prompt_ar": "تعديل المنشئ"},
        headers=headers_owner,
    ).status_code == 200
    assert client.put(
        f"/content/questions/{question_id}",
        json={**VALID_MCQ, "prompt_ar": "تعديل المدير"},
        headers=headers_admin,
    ).status_code == 200
    assert client.delete(f"/content/questions/{question_id}", headers=headers_admin).status_code == 204


def test_seeded_questions_are_admin_managed(client, db_session):
    teacher = make_teacher(client, db_session, "seeded-question-teacher@example.com")
    admin = register_and_login(client, "seeded-question-admin@example.com")
    set_role(db_session, "seeded-question-admin@example.com", UserRole.admin)
    question = db_session.query(Question).filter(Question.key == "lin-01").first()
    assert question is not None
    payload = {**VALID_MCQ, "prompt_ar": "محاولة تعديل محتوى مزروع"}

    assert client.put(
        f"/content/questions/{question.id}", json=payload, headers=auth(teacher)
    ).status_code == 403
    assert client.delete(
        f"/content/questions/{question.id}", headers=auth(teacher)
    ).status_code == 403
    assert client.put(
        f"/content/questions/{question.id}",
        json={**VALID_MCQ, "prompt_ar": "تعديل المدير للمحتوى المزروع"},
        headers=auth(admin),
    ).status_code == 200


def test_lessons_are_shared_read_only_and_managed_by_creator_or_admin(client, db_session):
    owner = make_teacher(client, db_session, "lesson-owner@example.com")
    other = make_teacher(client, db_session, "lesson-other@example.com")
    admin = register_and_login(client, "lesson-admin@example.com")
    set_role(db_session, "lesson-admin@example.com", UserRole.admin)
    topic_id = topic_id_by_slug(client, "linear-equations")
    url = f"/content/topics/{topic_id}/lessons"
    headers_owner, headers_other, headers_admin = auth(owner), auth(other), auth(admin)
    payload = {"title_ar": "درس مشترك", "body_md": "محتوى الدرس", "is_published": True}

    created = client.post(url, json=payload, headers=headers_owner)
    assert created.status_code == 201
    lesson_id = created.json()["id"]
    owner_user_id = db_session.query(Lesson).filter(Lesson.id == lesson_id).one().created_by_user_id
    assert owner_user_id is not None

    listed = client.get(url, headers=headers_other)
    assert listed.status_code == 200
    assert lesson_id in {lesson["id"] for lesson in listed.json()}
    changed = {**payload, "title_ar": "تعديل غير مصرح"}
    assert client.put(
        f"/content/lessons/{lesson_id}", json=changed, headers=headers_other
    ).status_code == 403
    assert client.delete(f"/content/lessons/{lesson_id}", headers=headers_other).status_code == 403

    assert client.put(
        f"/content/lessons/{lesson_id}",
        json={**payload, "title_ar": "تعديل المنشئ"},
        headers=headers_owner,
    ).status_code == 200
    assert client.put(
        f"/content/lessons/{lesson_id}",
        json={**payload, "title_ar": "تعديل المدير"},
        headers=headers_admin,
    ).status_code == 200
    assert client.delete(f"/content/lessons/{lesson_id}", headers=headers_admin).status_code == 204
