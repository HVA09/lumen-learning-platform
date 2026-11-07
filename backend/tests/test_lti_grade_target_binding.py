"""Regression tests proving AGS grade passback targets the exact launched LMS resource."""
from app.auth.sessions import create_browser_session
from app.models.assignment import AssignmentSubmission
from app.models.lti import LTIAGSGradeEvent, LTIAssignmentLink, LTIPlatform, LTIUserLink
from app.models.user import User
from tests.quiz_helpers import auth, make_student, make_teacher


def _create_assignment(client, teacher_token):
    response = client.post(
        "/assignments",
        json={"title": "LTI target binding", "description": "Target binding regression"},
        headers=auth(teacher_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _platform(db_session, suffix="one"):
    platform = LTIPlatform(
        name=f"Moodle sandbox {suffix}",
        issuer=f"https://moodle-{suffix}.example.test",
        client_id=f"client-{suffix}",
        deployment_id=f"deployment-{suffix}",
        auth_login_url=f"https://moodle-{suffix}.example.test/login",
        auth_token_url=f"https://moodle-{suffix}.example.test/token",
        jwks_url=f"https://moodle-{suffix}.example.test/jwks",
    )
    db_session.add(platform)
    db_session.flush()
    return platform


def _mapping(db_session, platform, assignment_id, resource_link_id):
    mapping = LTIAssignmentLink(
        platform_id=platform.id,
        assignment_id=assignment_id,
        deployment_id=platform.deployment_id,
        resource_link_id=resource_link_id,
        lineitem_url=f"{platform.issuer}/lineitems/{resource_link_id}",
        score_scope_allowed=True,
        score_maximum=100.0,
    )
    db_session.add(mapping)
    db_session.flush()
    return mapping


def _lti_session(db_session, user, platform, resource_link_id):
    access_token, _refresh_token, session = create_browser_session(db_session, user)
    session.lti_platform_id = platform.id
    session.lti_deployment_id = platform.deployment_id
    session.lti_resource_link_id = resource_link_id
    db_session.commit()
    return access_token


def test_grade_passback_is_bound_to_exact_resource_link_not_every_mapping(client, db_session):
    teacher_token = make_teacher(client, db_session, "lti-target-teacher@example.com")
    student_token = make_student(client, "lti-target-student@example.com")
    assignment_id = _create_assignment(client, teacher_token)
    student = db_session.query(User).filter_by(email="lti-target-student@example.com").one()
    platform = _platform(db_session)
    resource_a = _mapping(db_session, platform, assignment_id, "course-a-resource")
    resource_b = _mapping(db_session, platform, assignment_id, "course-b-resource")
    db_session.add(
        LTIUserLink(platform_id=platform.id, lti_subject="learner-a", user_id=student.id)
    )
    db_session.flush()

    # A distinct LTI browser session proves the learner launched resource A.
    access_token = _lti_session(db_session, student, platform, "course-a-resource")
    submitted = client.post(
        f"/assignments/{assignment_id}/submit",
        json={"written_answer": "answer from resource A"},
        headers=auth(access_token),
    )
    assert submitted.status_code == 200, submitted.text
    submission = db_session.get(AssignmentSubmission, submitted.json()["id"])
    assert submission.lti_assignment_link_id == resource_a.id

    graded = client.post(
        f"/assignments/{assignment_id}/submissions/{submission.id}/grade",
        json={"grade_percentage": 87, "feedback": "Good"},
        headers=auth(teacher_token),
    )
    assert graded.status_code == 200, graded.text

    events = (
        db_session.query(LTIAGSGradeEvent)
        .filter(LTIAGSGradeEvent.submission_id == submission.id)
        .all()
    )
    assert len(events) == 1
    assert events[0].assignment_link_id == resource_a.id
    assert events[0].assignment_link_id != resource_b.id
    assert events[0].score_given == 87.0


def test_non_lti_submission_never_broadcasts_to_mapped_lms_resources(client, db_session):
    teacher_token = make_teacher(client, db_session, "lti-no-target-teacher@example.com")
    student_token = make_student(client, "lti-no-target-student@example.com")
    assignment_id = _create_assignment(client, teacher_token)
    student = db_session.query(User).filter_by(email="lti-no-target-student@example.com").one()
    platform = _platform(db_session, "two")
    _mapping(db_session, platform, assignment_id, "resource-1")
    _mapping(db_session, platform, assignment_id, "resource-2")
    db_session.add(
        LTIUserLink(platform_id=platform.id, lti_subject="learner-no-launch", user_id=student.id)
    )
    db_session.flush()

    submitted = client.post(
        f"/assignments/{assignment_id}/submit",
        json={"written_answer": "ordinary Lumen submission"},
        headers=auth(student_token),
    )
    assert submitted.status_code == 200, submitted.text
    submission = db_session.get(AssignmentSubmission, submitted.json()["id"])
    assert submission.lti_assignment_link_id is None

    graded = client.post(
        f"/assignments/{assignment_id}/submissions/{submission.id}/grade",
        json={"grade_percentage": 91, "feedback": "Good"},
        headers=auth(teacher_token),
    )
    assert graded.status_code == 200, graded.text
    assert db_session.query(LTIAGSGradeEvent).filter_by(submission_id=submission.id).count() == 0


def test_lti_session_for_different_resource_or_assignment_has_no_passback_target(client, db_session):
    teacher_token = make_teacher(client, db_session, "lti-mismatch-teacher@example.com")
    student = make_student(client, "lti-mismatch-student@example.com")
    assignment_id = _create_assignment(client, teacher_token)
    student_user = db_session.query(User).filter_by(email="lti-mismatch-student@example.com").one()
    platform = _platform(db_session, "three")
    _mapping(db_session, platform, assignment_id, "resource-mapped")
    db_session.add(
        LTIUserLink(platform_id=platform.id, lti_subject="learner-mismatch", user_id=student_user.id)
    )
    db_session.flush()

    access_token = _lti_session(db_session, student_user, platform, "resource-not-mapped")
    submitted = client.post(
        f"/assignments/{assignment_id}/submit",
        json={"written_answer": "from an unrelated resource"},
        headers=auth(access_token),
    )
    assert submitted.status_code == 200, submitted.text
    submission = db_session.get(AssignmentSubmission, submitted.json()["id"])
    assert submission.lti_assignment_link_id is None
