"""
اختبارات الواجبات: المعلّم ينشئ ويقيّم يدويًا، الطالب يسلّم إجابة مكتوبة (بدون أي تقييم آلي)
"""
from app.models.user import UserRole
from tests.quiz_helpers import auth, make_student, make_teacher, register_and_login, set_role


def _create_assignment(client, teacher_token, **overrides):
    payload = {
        "title": "واجب المعادلات",
        "description": "حل 5 معادلات خطية مع شرح الخطوات",
        "rubric_criteria": ["  يشرح الخطوات  ", "", "يتحقق من الحل"],
        **overrides,
    }
    response = client.post("/assignments", json=payload, headers=auth(teacher_token))
    assert response.status_code == 201, response.text
    return response.json()


def _submit(client, student_token, assignment_id, answer="حللت المعادلة بطرح 3 من الطرفين ثم القسمة على 2"):
    return client.post(
        f"/assignments/{assignment_id}/submit",
        json={"written_answer": answer},
        headers=auth(student_token),
    )


def _grade(client, teacher_token, assignment_id, submission_id, percentage=85, feedback="أحسنت"):
    return client.post(
        f"/assignments/{assignment_id}/submissions/{submission_id}/grade",
        json={"grade_percentage": percentage, "feedback": feedback},
        headers=auth(teacher_token),
    )


def test_teacher_creates_assignment_and_students_can_read_it(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "reader1@example.com")

    assignment = _create_assignment(client, teacher)
    assert assignment["rubric_criteria"] == ["يشرح الخطوات", "يتحقق من الحل"]  # تُنظَّف المسافات والفراغات

    fetched = client.get(f"/assignments/{assignment['id']}", headers=auth(student))
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "واجب المعادلات"


def test_student_cannot_create_assignment(client):
    student = make_student(client, "sneaky@example.com")
    response = client.post(
        "/assignments", json={"title": "و", "description": "..."}, headers=auth(student)
    )
    assert response.status_code == 403


def test_assignments_require_authentication(client):
    assert client.get("/assignments").status_code == 401
    assert client.get("/assignments/1").status_code == 401
    assert client.post("/assignments/1/submit", json={"written_answer": "x"}).status_code == 401
    assert client.post("/assignments", json={"title": "و", "description": "."}).status_code == 401


def test_list_shows_my_status_and_teacher_only_counts(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "lister@example.com")
    assignment = _create_assignment(client, teacher)

    before = client.get("/assignments", headers=auth(student)).json()
    item = next(a for a in before if a["id"] == assignment["id"])
    assert item["my_status"] is None
    assert item["can_manage"] is False
    assert item["submissions_count"] is None  # الطالب ما يشوف أعداد التسليمات

    _submit(client, student, assignment["id"])

    after = client.get("/assignments", headers=auth(student)).json()
    assert next(a for a in after if a["id"] == assignment["id"])["my_status"] == "submitted"

    teacher_list = client.get("/assignments", headers=auth(teacher)).json()
    teacher_item = next(a for a in teacher_list if a["id"] == assignment["id"])
    assert teacher_item["can_manage"] is True
    assert teacher_item["submissions_count"] == 1
    assert teacher_item["pending_grading_count"] == 1


def test_submission_waits_for_teacher_grading(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "waiter@example.com")
    assignment = _create_assignment(client, teacher)

    response = _submit(client, student, assignment["id"])
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    assert body["grade_percentage"] is None
    assert body["feedback"] is None
    assert body["is_late"] is False


def test_student_can_edit_submission_until_it_is_graded(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "editor@example.com")
    assignment = _create_assignment(client, teacher)

    _submit(client, student, assignment["id"], "إجابة أولى")
    second = _submit(client, student, assignment["id"], "إجابة معدّلة")
    assert second.status_code == 200
    assert second.json()["written_answer"] == "إجابة معدّلة"

    mine = client.get(f"/assignments/{assignment['id']}/my-submission", headers=auth(student)).json()
    assert mine["written_answer"] == "إجابة معدّلة"


def test_teacher_lists_submissions_with_student_names(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "named@example.com")
    client.patch("/users/me", json={"full_name": "سعد الأحمد"}, headers=auth(student))
    assignment = _create_assignment(client, teacher)
    _submit(client, student, assignment["id"])

    response = client.get(f"/assignments/{assignment['id']}/submissions", headers=auth(teacher))
    assert response.status_code == 200
    assert [s["student_name"] for s in response.json()] == ["سعد الأحمد"]


def test_teacher_grades_submission_and_student_sees_result_and_notification(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "graded@example.com")
    assignment = _create_assignment(client, teacher)
    submission = _submit(client, student, assignment["id"]).json()

    graded = _grade(client, teacher, assignment["id"], submission["id"], 85, "شرح جيد لكن ينقصه التحقق")
    assert graded.status_code == 200
    assert graded.json()["status"] == "graded"
    assert graded.json()["grade_percentage"] == 85.0

    mine = client.get(f"/assignments/{assignment['id']}/my-submission", headers=auth(student)).json()
    assert mine["status"] == "graded"
    assert mine["grade_percentage"] == 85.0
    assert "التحقق" in mine["feedback"]
    assert mine["graded_at"] is not None

    notifications = client.get("/notifications", headers=auth(student)).json()
    assert any(n["title"] == "تم تقييم واجبك" and "85%" in n["body"] for n in notifications)


def test_teacher_is_notified_of_first_submission(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "notifier@example.com")
    assignment = _create_assignment(client, teacher)
    _submit(client, student, assignment["id"])

    notifications = client.get("/notifications", headers=auth(teacher)).json()
    assert any(n["title"] == "تسليم جديد" for n in notifications)


def test_graded_submission_is_locked_for_student(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "locked@example.com")
    assignment = _create_assignment(client, teacher)
    submission = _submit(client, student, assignment["id"]).json()
    _grade(client, teacher, assignment["id"], submission["id"])

    response = _submit(client, student, assignment["id"], "محاولة تعديل بعد التقييم")
    assert response.status_code == 409


def test_teacher_can_regrade(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "regrade@example.com")
    assignment = _create_assignment(client, teacher)
    submission = _submit(client, student, assignment["id"]).json()

    _grade(client, teacher, assignment["id"], submission["id"], 50)
    regraded = _grade(client, teacher, assignment["id"], submission["id"], 90)
    assert regraded.status_code == 200
    assert regraded.json()["grade_percentage"] == 90.0


def test_grade_must_be_between_0_and_100(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "range@example.com")
    assignment = _create_assignment(client, teacher)
    submission = _submit(client, student, assignment["id"]).json()

    assert _grade(client, teacher, assignment["id"], submission["id"], 150).status_code == 422
    assert _grade(client, teacher, assignment["id"], submission["id"], -5).status_code == 422


def test_student_cannot_grade(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "selfgrader@example.com")
    assignment = _create_assignment(client, teacher)
    submission = _submit(client, student, assignment["id"]).json()

    assert _grade(client, student, assignment["id"], submission["id"], 100).status_code == 403


def test_only_creator_or_admin_can_manage_submissions(client, db_session):
    teacher = make_teacher(client, db_session, "teacher-a@example.com")
    other_teacher = make_teacher(client, db_session, "teacher-b@example.com")
    student = make_student(client, "shared@example.com")
    assignment = _create_assignment(client, teacher)
    submission = _submit(client, student, assignment["id"]).json()

    url = f"/assignments/{assignment['id']}/submissions"
    assert client.get(url, headers=auth(student)).status_code == 403
    assert client.get(url, headers=auth(other_teacher)).status_code == 403
    assert _grade(client, other_teacher, assignment["id"], submission["id"]).status_code == 403
    assert client.get(url, headers=auth(teacher)).status_code == 200

    admin = register_and_login(client, "assignment-admin@example.com")
    set_role(db_session, "assignment-admin@example.com", UserRole.admin)
    assert client.get(url, headers=auth(admin)).status_code == 200


def test_late_submission_is_flagged(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "late@example.com")
    assignment = _create_assignment(client, teacher, due_at="2020-01-01T00:00:00Z")

    response = _submit(client, student, assignment["id"])
    assert response.status_code == 200
    assert response.json()["is_late"] is True


def test_blank_answer_is_rejected(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "blank-answer@example.com")
    assignment = _create_assignment(client, teacher)

    assert _submit(client, student, assignment["id"], "   ").status_code == 422
    assert _submit(client, student, assignment["id"], "").status_code == 422


def test_passing_grade_unlocks_assignment_achievement(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "achiever@example.com")
    assignment = _create_assignment(client, teacher)
    submission = _submit(client, student, assignment["id"]).json()
    _grade(client, teacher, assignment["id"], submission["id"], 70)

    achievements = client.get("/gamification/my-achievements", headers=auth(student)).json()
    assert next(a for a in achievements if a["key"] == "assignment_first")["unlocked_at"] is not None


def test_failing_grade_does_not_unlock_assignment_achievement(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "almost@example.com")
    assignment = _create_assignment(client, teacher)
    submission = _submit(client, student, assignment["id"]).json()
    _grade(client, teacher, assignment["id"], submission["id"], 69)

    achievements = client.get("/gamification/my-achievements", headers=auth(student)).json()
    assert next(a for a in achievements if a["key"] == "assignment_first")["unlocked_at"] is None


def test_creator_can_delete_assignment_but_students_cannot(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "deleter@example.com")
    assignment = _create_assignment(client, teacher)

    assert client.delete(f"/assignments/{assignment['id']}", headers=auth(student)).status_code == 403
    assert client.delete(f"/assignments/{assignment['id']}", headers=auth(teacher)).status_code == 204
    assert client.get(f"/assignments/{assignment['id']}", headers=auth(teacher)).status_code == 404


def test_get_my_submission_returns_null_before_submitting(client, db_session):
    teacher = make_teacher(client, db_session)
    student = make_student(client, "fresh@example.com")
    assignment = _create_assignment(client, teacher)

    response = client.get(f"/assignments/{assignment['id']}/my-submission", headers=auth(student))
    assert response.status_code == 200
    assert response.json() is None


def test_submit_to_unknown_assignment_404(client):
    student = make_student(client, "lost@example.com")
    assert _submit(client, student, 999999).status_code == 404



def test_ags_grade_event_targets_only_the_submission_resource_link(client, db_session):
    from app.auth.security import decode_token
    from app.models.lti import LTIAGSGradeEvent, LTIAssignmentLink, LTIPlatform, LTIUserLink
    from app.models.user import User

    teacher = make_teacher(client, db_session, "ags-teacher@example.com")
    student_token = make_student(client, "ags-student@example.com")
    student = db_session.query(User).filter(User.email == "ags-student@example.com").one()
    assignment = _create_assignment(client, teacher)

    platform = LTIPlatform(
        name="AGS mapping test",
        issuer="https://moodle.example.com",
        client_id="ags-mapping-client",
        deployment_id="ags-deployment",
        auth_login_url="https://moodle.example.com/auth",
        auth_token_url="https://moodle.example.com/token",
        jwks_url="https://moodle.example.com/jwks",
    )
    db_session.add(platform)
    db_session.flush()
    mapping_a = LTIAssignmentLink(
        platform_id=platform.id,
        assignment_id=assignment["id"],
        deployment_id=platform.deployment_id,
        resource_link_id="resource-A",
        lineitem_url="https://moodle.example.com/lineitems/A",
        score_scope_allowed=True,
        score_maximum=100,
    )
    mapping_b = LTIAssignmentLink(
        platform_id=platform.id,
        assignment_id=assignment["id"],
        deployment_id=platform.deployment_id,
        resource_link_id="resource-B",
        lineitem_url="https://moodle.example.com/lineitems/B",
        score_scope_allowed=True,
        score_maximum=100,
    )
    db_session.add_all([mapping_a, mapping_b])
    db_session.add(LTIUserLink(
        platform_id=platform.id,
        lti_subject="ags-external-student",
        user_id=student.id,
    ))
    db_session.flush()

    session_id = decode_token(student_token)["sid"]
    from app.models.auth_session import AuthSession
    browser_session = db_session.get(AuthSession, session_id)
    assert browser_session is not None
    browser_session.lti_platform_id = platform.id
    browser_session.lti_deployment_id = platform.deployment_id
    browser_session.lti_resource_link_id = "resource-A"
    browser_session.lti_subject = "ags-external-student"
    db_session.commit()

    submitted = _submit(client, student_token, assignment["id"])
    assert submitted.status_code == 200, submitted.text
    submission_id = submitted.json()["id"]
    submission = db_session.get(__import__("app.models.assignment", fromlist=["AssignmentSubmission"]).AssignmentSubmission, submission_id)
    assert submission.lti_assignment_link_id == mapping_a.id
    assert submission.lti_subject == "ags-external-student"

    graded = _grade(client, teacher, assignment["id"], submission_id, 84)
    assert graded.status_code == 200, graded.text
    events = db_session.query(LTIAGSGradeEvent).filter_by(submission_id=submission_id).all()
    assert len(events) == 1
    assert events[0].assignment_link_id == mapping_a.id
    assert events[0].grade_version == 1

    unrelated = _create_assignment(client, teacher, title="واجب غير مرتبط برابط LTI")
    unrelated_submission = _submit(client, student_token, unrelated["id"])
    assert unrelated_submission.status_code == 200
    unrelated_id = unrelated_submission.json()["id"]
    _grade(client, teacher, unrelated["id"], unrelated_id, 91)
    assert db_session.query(LTIAGSGradeEvent).filter_by(submission_id=unrelated_id).count() == 0
