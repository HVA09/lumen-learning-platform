"""
اختبارات الاختبارات (Quiz): التصحيح والإتقان يصيرون بالسيرفر فقط، وقفل المواضيع بالمتطلّبات
"""
from app.models.question import Question
from app.models.quiz_attempt import QuizAttempt
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.user import UserRole
from tests.quiz_helpers import (
    auth,
    correct_answer_payload,
    make_student,
    make_teacher,
    register_and_login,
    take_quiz,
    topic_id_by_slug,
    set_role,
)


def _start(client, token, topic_id, mode="practice"):
    return client.post(f"/quiz/topics/{topic_id}/start", json={"mode": mode}, headers=auth(token))


def test_start_quiz_requires_authentication(client):
    topic_id = topic_id_by_slug(client, "linear-equations")
    response = client.post(f"/quiz/topics/{topic_id}/start", json={"mode": "practice"})
    assert response.status_code == 401


def test_practice_quiz_returns_five_questions_without_answers(client):
    token = make_student(client, "quizreader@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")

    response = _start(client, token, topic_id)
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "practice"
    assert body["pass_percentage"] is None
    assert body["resumed"] is False
    assert len(body["questions"]) == 5
    for question in body["questions"]:
        assert set(question) == {"id", "kind", "prompt_ar", "choices", "difficulty"}
        if question["kind"] == "mcq":
            assert len(question["choices"]) >= 2
        if question["kind"] == "true_false":
            assert question["choices"] == ["صحيح", "خطأ"]
        if question["kind"] in ("numeric", "short_text"):
            assert question["choices"] is None
    assert "correct_answer" not in response.text
    assert "explanation" not in response.text


def test_gateway_quiz_uses_ten_questions_and_reports_pass_threshold(client):
    token = make_student(client, "gatewayreader@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")

    body = _start(client, token, topic_id, "gateway").json()
    assert body["mode"] == "gateway"
    assert body["pass_percentage"] == 80.0
    assert len(body["questions"]) == 10
    assert len({q["id"] for q in body["questions"]}) == 10


def test_locked_topic_rejects_quiz_for_student(client):
    token = make_student(client, "lockedstudent@example.com")
    derivatives_id = topic_id_by_slug(client, "derivatives-intro")

    response = _start(client, token, derivatives_id)
    assert response.status_code == 403
    assert "المعادلات الخطية" in response.json()["detail"]


def test_admin_bypasses_topic_lock(client, db_session):
    admin_token = register_and_login(client, "adminquiz@example.com")
    set_role(db_session, "adminquiz@example.com", UserRole.admin)
    derivatives_id = topic_id_by_slug(client, "derivatives-intro")
    assert _start(client, admin_token, derivatives_id).status_code == 200


def test_passing_prerequisite_gateway_unlocks_dependent_topic_quiz(client, db_session):
    token = make_student(client, "unlocker@example.com")
    linear_id = topic_id_by_slug(client, "linear-equations")
    derivatives_id = topic_id_by_slug(client, "derivatives-intro")

    assert _start(client, token, derivatives_id).status_code == 403
    take_quiz(client, db_session, token, linear_id, mode="gateway", correct=True)
    assert _start(client, token, derivatives_id).status_code == 200


def test_perfect_gateway_submission_scores_100_and_passes(client, db_session):
    token = make_student(client, "perfect@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")

    result = take_quiz(client, db_session, token, topic_id, mode="gateway", correct=True)
    assert result["score_percentage"] == 100.0
    assert result["correct_count"] == result["total"] == 10
    assert result["passed"] is True
    assert result["mastery_percentage"] == 100.0
    assert result["gateway_quiz_passed"] is True
    unlocked = {a["key"] for a in result["new_achievements"]}
    assert {"first_quiz", "perfect_quiz", "gateway_first"} <= unlocked
    for item in result["results"]:
        assert item["correct"] is True
        assert item["correct_answer_text"]


def test_empty_submission_scores_zero_and_shows_explanations(client, db_session):
    token = make_student(client, "blank@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")

    result = take_quiz(client, db_session, token, topic_id, mode="gateway", correct=False)
    assert result["score_percentage"] == 0.0
    assert result["passed"] is False
    assert result["mastery_percentage"] == 0.0
    assert result["gateway_quiz_passed"] is False
    assert all(item["correct"] is False for item in result["results"])
    assert all(item["explanation_ar"] for item in result["results"])
    assert all(item["correct_answer_text"] for item in result["results"])


def test_gateway_below_threshold_does_not_unlock_dependent_topic(client, db_session):
    token = make_student(client, "belowthreshold@example.com")
    linear_id = topic_id_by_slug(client, "linear-equations")
    derivatives_id = topic_id_by_slug(client, "derivatives-intro")

    assert _start(client, token, derivatives_id).status_code == 403

    attempt = _start(client, token, linear_id, "gateway").json()
    questions = attempt["questions"]
    assert len(questions) == 10

    answers = []
    for index, public_question in enumerate(questions):
        row = db_session.get(Question, public_question["id"])
        correct_answer = correct_answer_payload(row)

        if index < 7:
            answer = correct_answer
        elif row.kind == "mcq":
            answer = (int(correct_answer) + 1) % len(row.choices)
        elif row.kind == "true_false":
            answer = not bool(correct_answer)
        elif row.kind == "numeric":
            answer = (
                float(correct_answer) + float(row.tolerance or 0.0) + 1.0
            )
        elif row.kind == "short_text":
            answer = "__incorrect_test_answer__"
        else:
            raise AssertionError(f"Unsupported seeded question kind: {row.kind}")

        answers.append({"question_id": row.id, "answer": answer})

    submitted = client.post(
        f"/quiz/attempts/{attempt['attempt_id']}/submit",
        json={"answers": answers},
        headers=auth(token),
    )
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()
    assert result["total"] == 10
    assert result["correct_count"] == 7
    assert result["score_percentage"] == 70.0
    assert result["passed"] is False
    assert result["gateway_quiz_passed"] is False

    still_locked = _start(client, token, derivatives_id)
    assert still_locked.status_code == 403
    assert "المعادلات الخطية" in still_locked.json()["detail"]


def test_practice_quiz_never_sets_gateway_passed(client, db_session):
    token = make_student(client, "practiceonly@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")

    result = take_quiz(client, db_session, token, topic_id, mode="practice", correct=True)
    assert result["score_percentage"] == 100.0
    assert result["passed"] is None
    assert result["gateway_quiz_passed"] is False


def test_failed_gateway_has_retry_cooldown_but_practice_is_allowed(client, db_session):
    token = make_student(client, "cooldown@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")

    take_quiz(client, db_session, token, topic_id, mode="gateway", correct=False)
    retry = _start(client, token, topic_id, "gateway")
    assert retry.status_code == 429
    assert "دقيقة" in retry.json()["detail"]
    assert _start(client, token, topic_id, "practice").status_code == 200


def test_client_supplied_score_is_ignored(client, db_session):
    token = make_student(client, "fakescore@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id, "gateway").json()

    response = client.post(
        f"/quiz/attempts/{attempt['attempt_id']}/submit",
        json={"answers": [], "score_percentage": 100, "passed": True, "mastery_percentage": 100},
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["score_percentage"] == 0.0
    assert response.json()["gateway_quiz_passed"] is False


def test_mastery_is_moving_average_of_attempts(client, db_session):
    token = make_student(client, "average@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")

    first = take_quiz(client, db_session, token, topic_id, mode="practice", correct=True)
    assert first["mastery_percentage"] == 100.0
    second = take_quiz(client, db_session, token, topic_id, mode="practice", correct=False)
    assert second["mastery_percentage"] == 50.0

    mastery = client.get(f"/curriculum/topics/{topic_id}/mastery", headers=auth(token)).json()
    assert mastery["mastery_percentage"] == 50.0
    assert mastery["attempts_count"] == 2
    assert mastery["last_practiced_at"] is not None


def test_cannot_submit_same_attempt_twice(client):
    token = make_student(client, "twice@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id).json()
    url = f"/quiz/attempts/{attempt['attempt_id']}/submit"

    assert client.post(url, json={"answers": []}, headers=auth(token)).status_code == 200
    assert client.post(url, json={"answers": []}, headers=auth(token)).status_code == 409


def test_cannot_submit_someone_elses_attempt(client):
    owner = make_student(client, "attemptowner@example.com")
    intruder = make_student(client, "attemptintruder@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, owner, topic_id).json()

    response = client.post(
        f"/quiz/attempts/{attempt['attempt_id']}/submit", json={"answers": []}, headers=auth(intruder)
    )
    assert response.status_code == 404


def test_unsubmitted_attempt_is_resumed_with_same_questions(client):
    token = make_student(client, "resume@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")

    first = _start(client, token, topic_id).json()
    second = _start(client, token, topic_id).json()
    assert second["resumed"] is True
    assert second["attempt_id"] == first["attempt_id"]
    assert [q["id"] for q in second["questions"]] == [q["id"] for q in first["questions"]]


def test_history_lists_submitted_attempts_newest_first(client, db_session):
    token = make_student(client, "history@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")

    take_quiz(client, db_session, token, topic_id, mode="practice", correct=False)
    take_quiz(client, db_session, token, topic_id, mode="practice", correct=True)

    history = client.get(f"/quiz/topics/{topic_id}/history", headers=auth(token)).json()
    assert [h["score_percentage"] for h in history] == [100.0, 0.0]
    assert all(h["mode"] == "practice" for h in history)


def test_topic_without_questions_returns_409(client, db_session):
    token = make_student(client, "noquestions@example.com")
    subject = db_session.query(Subject).first()
    topic = Topic(subject_id=subject.id, slug="empty-topic-for-tests", name_ar="فارغ", name_en="Empty", order_index=99)
    db_session.add(topic)
    db_session.commit()

    response = _start(client, token, topic.id)
    assert response.status_code == 409


def test_start_quiz_unknown_topic_404(client):
    token = make_student(client, "unknowntopicquiz@example.com")
    assert _start(client, token, 999999).status_code == 404


def test_malformed_answers_are_marked_wrong_not_errors(client):
    token = make_student(client, "garbage@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id, "gateway").json()

    garbage = {"mcq": 99, "true_false": "؟", "numeric": "abc", "short_text": "zzz"}
    answers = [{"question_id": q["id"], "answer": garbage[q["kind"]]} for q in attempt["questions"]]
    response = client.post(
        f"/quiz/attempts/{attempt['attempt_id']}/submit", json={"answers": answers}, headers=auth(token)
    )
    assert response.status_code == 200
    assert response.json()["score_percentage"] == 0.0


def test_answer_must_be_a_simple_value(client):
    token = make_student(client, "nested@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id).json()
    response = client.post(
        f"/quiz/attempts/{attempt['attempt_id']}/submit",
        json={"answers": [{"question_id": attempt["questions"][0]["id"], "answer": {"x": 1}}]},
        headers=auth(token),
    )
    assert response.status_code == 422


def test_answers_for_questions_outside_the_attempt_are_rejected(client):
    token = make_student(client, "outsider@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id).json()

    response = client.post(
        f"/quiz/attempts/{attempt['attempt_id']}/submit",
        json={"answers": [{"question_id": 999999, "answer": 1}]},
        headers=auth(token),
    )
    assert response.status_code == 422


def test_duplicate_question_answers_are_rejected(client):
    token = make_student(client, "duplicateanswers@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id).json()
    question_id = attempt["questions"][0]["id"]

    response = client.post(
        f"/quiz/attempts/{attempt['attempt_id']}/submit",
        json={"answers": [
            {"question_id": question_id, "answer": 1},
            {"question_id": question_id, "answer": 2},
        ]},
        headers=auth(token),
    )
    assert response.status_code == 422


def test_partial_answers_are_saved_and_restored_on_resume(client):
    token = make_student(client, "draftresume@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id).json()
    answers = [
        {"question_id": question["id"], "answer": 1 if index == 0 else None}
        for index, question in enumerate(attempt["questions"])
    ]

    saved = client.put(
        f"/quiz/attempts/{attempt['attempt_id']}/answers",
        json={"answers": answers},
        headers=auth(token),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["answer_count"] == 1

    resumed = _start(client, token, topic_id)
    assert resumed.status_code == 200
    assert resumed.json()["resumed"] is True
    assert resumed.json()["saved_answers"][str(attempt["questions"][0]["id"])] == 1
    assert all(
        resumed.json()["saved_answers"][str(question["id"])] is None
        for question in attempt["questions"][1:]
    )


def test_draft_save_rejects_unknown_duplicate_and_incomplete_maps(client):
    token = make_student(client, "draftvalidation@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id).json()
    url = f"/quiz/attempts/{attempt['attempt_id']}/answers"
    headers = auth(token)
    first_id = attempt["questions"][0]["id"]

    unknown = [{"question_id": 999999, "answer": 1}] + [
        {"question_id": question["id"], "answer": None}
        for question in attempt["questions"][1:]
    ]
    assert client.put(url, json={"answers": unknown}, headers=headers).status_code == 422

    duplicate = [
        {"question_id": first_id, "answer": 1},
        {"question_id": first_id, "answer": 2},
    ] + [
        {"question_id": question["id"], "answer": None}
        for question in attempt["questions"][1:]
    ]
    assert client.put(url, json={"answers": duplicate}, headers=headers).status_code == 422
    assert client.put(
        url, json={"answers": [{"question_id": first_id, "answer": 1}]}, headers=headers
    ).status_code == 422


def test_draft_save_rejects_another_users_attempt(client):
    owner = make_student(client, "draftowner@example.com")
    intruder = make_student(client, "draftintruder@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, owner, topic_id).json()
    answers = [{"question_id": question["id"], "answer": None} for question in attempt["questions"]]

    response = client.put(
        f"/quiz/attempts/{attempt['attempt_id']}/answers",
        json={"answers": answers},
        headers=auth(intruder),
    )
    assert response.status_code == 404


def test_submitted_attempt_rejects_later_draft_saves(client):
    token = make_student(client, "draftsubmitted@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id).json()
    url = f"/quiz/attempts/{attempt['attempt_id']}"
    assert client.post(f"{url}/submit", json={"answers": []}, headers=auth(token)).status_code == 200
    answers = [{"question_id": question["id"], "answer": None} for question in attempt["questions"]]
    assert client.put(f"{url}/answers", json={"answers": answers}, headers=auth(token)).status_code == 409


def test_attempt_snapshot_is_used_for_resume_and_grading_after_question_edit(client, db_session):
    token = make_student(client, "snapshotimmutable@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id).json()
    first = attempt["questions"][0]
    question = db_session.get(Question, first["id"])
    original_prompt = question.prompt_ar
    original_answer = correct_answer_payload(question)
    original_choices = question.choices

    question.prompt_ar = "تعريف جديد لا يجب أن يظهر في المحاولة المفتوحة"
    question.correct_answer = False if question.kind == "true_false" else "__changed_definition__"
    question.choices = ["خيار جديد", "خيار آخر"] if question.kind == "mcq" else original_choices
    db_session.commit()

    resumed = _start(client, token, topic_id).json()
    restored = next(item for item in resumed["questions"] if item["id"] == first["id"])
    assert restored["prompt_ar"] == original_prompt
    assert restored["choices"] == first["choices"]

    submitted = client.post(
        f"/quiz/attempts/{attempt['attempt_id']}/submit",
        json={"answers": [{"question_id": first["id"], "answer": original_answer}]},
        headers=auth(token),
    )
    assert submitted.status_code == 200, submitted.text
    graded = next(item for item in submitted.json()["results"] if item["question_id"] == first["id"])
    assert graded["prompt_ar"] == original_prompt
    assert graded["correct"] is True



def test_class_context_is_validated_and_preserved_when_resuming(client, db_session):
    teacher = make_teacher(client, db_session, "quiz-context-teacher@example.com")
    student = make_student(client, "quiz-context-student@example.com")
    created = client.post("/classes", json={"name": "فصل سياق الاختبار"}, headers=auth(teacher))
    assert created.status_code == 201
    section = created.json()
    joined = client.post(
        "/classes/join", json={"invite_code": section["invite_code"]}, headers=auth(student)
    )
    assert joined.status_code == 200
    topic_id = topic_id_by_slug(client, "linear-equations")

    first = client.post(
        f"/quiz/topics/{topic_id}/start",
        json={"mode": "practice", "class_section_id": section["id"]},
        headers=auth(student),
    )
    assert first.status_code == 200, first.text
    assert first.json()["class_section_id"] == section["id"]

    resumed_without_context = _start(client, student, topic_id)
    assert resumed_without_context.status_code == 200
    assert resumed_without_context.json()["resumed"] is True
    assert resumed_without_context.json()["class_section_id"] == section["id"]

    explicit_personal = client.post(
        f"/quiz/topics/{topic_id}/start",
        json={"mode": "practice", "class_section_id": None},
        headers=auth(student),
    )
    assert explicit_personal.status_code == 409


def test_class_context_rejects_non_members_and_staff(client, db_session):
    teacher = make_teacher(client, db_session, "quiz-context-owner@example.com")
    student = make_student(client, "quiz-context-outsider@example.com")
    created = client.post("/classes", json={"name": "فصل خاص"}, headers=auth(teacher)).json()
    topic_id = topic_id_by_slug(client, "linear-equations")

    outsider = client.post(
        f"/quiz/topics/{topic_id}/start",
        json={"mode": "practice", "class_section_id": created["id"]},
        headers=auth(student),
    )
    assert outsider.status_code == 403

    staff = client.post(
        f"/quiz/topics/{topic_id}/start",
        json={"mode": "practice", "class_section_id": created["id"]},
        headers=auth(teacher),
    )
    assert staff.status_code == 403


def test_new_attempt_captures_role_provenance(client, db_session):
    token = make_student(client, "roleprovenance@example.com")
    topic_id = topic_id_by_slug(client, "linear-equations")
    attempt = _start(client, token, topic_id).json()
    row = db_session.get(QuizAttempt, attempt["attempt_id"])
    assert row.user_role_at_creation == UserRole.user.value
    assert row.question_definition_snapshots
    assert row.draft_answers == {}
