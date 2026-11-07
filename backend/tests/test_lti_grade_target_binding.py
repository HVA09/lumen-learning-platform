"""Regression tests for resource-bound AGS passback and delivery ordering."""
import asyncio
import secrets
from datetime import datetime, timedelta, timezone

from app.auth.sessions import create_browser_session
from app.models.auth_session import AuthSession
from app.models.assignment import AssignmentSubmission
from app.models.lti import LTIAGSGradeEvent, LTIAuthCode, LTIAssignmentLink, LTIPlatform, LTIUserLink
from app.models.user import User
from app.services import lti_service as lti_service_module
from app.services.lti_service import hash_opaque_token
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


def test_grade_passback_is_bound_to_exact_resource_link_not_every_mapping(client, db_session, monkeypatch):
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

    # A re-grade must advance the version but retain the same exact target.
    # Simulate a backwards-moving application clock on re-grade. The score
    # timestamp must still increase because the submission row is serialized.
    from app.routers import assignments as assignments_router

    previous_timestamp = events[0].created_at
    if previous_timestamp.tzinfo is None:
        previous_timestamp = previous_timestamp.replace(tzinfo=timezone.utc)

    class RewoundClock:
        @staticmethod
        def now(tz=None):
            return previous_timestamp - timedelta(seconds=1)

    monkeypatch.setattr(assignments_router, "datetime", RewoundClock)

    regraded = client.post(
        f"/assignments/{assignment_id}/submissions/{submission.id}/grade",
        json={"grade_percentage": 93, "feedback": "Regraded"},
        headers=auth(teacher_token),
    )
    assert regraded.status_code == 200, regraded.text
    events = (
        db_session.query(LTIAGSGradeEvent)
        .filter(LTIAGSGradeEvent.submission_id == submission.id)
        .order_by(LTIAGSGradeEvent.grade_version)
        .all()
    )
    assert [event.grade_version for event in events] == [1, 2]
    assert [event.assignment_link_id for event in events] == [resource_a.id, resource_a.id]
    assert [event.score_given for event in events] == [87.0, 93.0]
    assert events[1].score_timestamp > events[0].score_timestamp


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



def test_lti_exchange_copies_verified_resource_context_into_new_browser_session(client, db_session):
    make_student(client, "lti-exchange-context@example.com")
    user = db_session.query(User).filter_by(email="lti-exchange-context@example.com").one()
    platform = _platform(db_session, "exchange")
    code = secrets.token_urlsafe(40)
    now = datetime.now(timezone.utc)
    db_session.add(
        LTIAuthCode(
            code_hash=hash_opaque_token(code),
            user_id=user.id,
            token_version=user.token_version,
            lti_platform_id=platform.id,
            lti_deployment_id=platform.deployment_id,
            lti_resource_link_id="verified-resource-77",
            expires_at=now + timedelta(seconds=60),
        )
    )
    db_session.commit()

    response = client.post("/lti/exchange-code", json={"code": code})
    assert response.status_code == 200, response.text
    sessions = db_session.query(AuthSession).filter(AuthSession.user_id == user.id).all()
    lti_sessions = [row for row in sessions if row.lti_platform_id == platform.id]
    assert len(lti_sessions) == 1
    assert lti_sessions[0].lti_deployment_id == platform.deployment_id
    assert lti_sessions[0].lti_resource_link_id == "verified-resource-77"


def test_ags_retry_reserves_a_new_timestamp_for_each_delivery_attempt(client, db_session, monkeypatch):
    teacher_token = make_teacher(client, db_session, "lti-retry-teacher@example.com")
    make_student(client, "lti-retry-student@example.com")
    assignment_id = _create_assignment(client, teacher_token)
    student = db_session.query(User).filter_by(email="lti-retry-student@example.com").one()
    platform = _platform(db_session, "retry")
    _mapping(db_session, platform, assignment_id, "retry-resource")
    db_session.add(LTIUserLink(platform_id=platform.id, lti_subject="retry-learner", user_id=student.id))
    db_session.flush()

    access_token = _lti_session(db_session, student, platform, "retry-resource")
    submitted = client.post(
        f"/assignments/{assignment_id}/submit",
        json={"written_answer": "retry test"},
        headers=auth(access_token),
    )
    assert submitted.status_code == 200, submitted.text
    submission_id = submitted.json()["id"]
    submission = db_session.get(AssignmentSubmission, submission_id)
    graded = client.post(
        f"/assignments/{assignment_id}/submissions/{submission_id}/grade",
        json={"grade_percentage": 76, "feedback": "Retry me"},
        headers=auth(teacher_token),
    )
    assert graded.status_code == 200, graded.text
    event = db_session.query(LTIAGSGradeEvent).filter_by(submission_id=submission_id).one()
    event_id = event.id
    graded_at = db_session.get(AssignmentSubmission, submission_id).graded_at

    timestamps = []
    async def fail_once(_platform, _lineitem, payload):
        timestamps.append(payload["timestamp"])
        if len(timestamps) == 1:
            raise TimeoutError("simulated uncertain response")

    monkeypatch.setattr(lti_service_module, "post_lti_ags_score", fail_once)
    assert asyncio.run(lti_service_module.dispatch_lti_grade_event(db_session, event_id)) is False

    event = db_session.get(LTIAGSGradeEvent, event_id)
    assert event.status == "pending"
    # A retry must reserve a timestamp later than the uncertain first attempt.
    event.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    async def succeed(_platform, _lineitem, payload):
        timestamps.append(payload["timestamp"])

    monkeypatch.setattr(lti_service_module, "post_lti_ags_score", succeed)
    assert asyncio.run(lti_service_module.dispatch_lti_grade_event(db_session, event_id)) is True
    assert len(timestamps) == 2
    assert timestamps[1] > timestamps[0]
    event = db_session.get(LTIAGSGradeEvent, event_id)
    assert event.status == "sent"
    assert event.attempts == 2
    db_session.refresh(submission)
    assert submission.graded_at == graded_at


def test_older_pending_grade_event_is_superseded_before_delivery(client, db_session, monkeypatch):
    teacher_token = make_teacher(client, db_session, "lti-stale-teacher@example.com")
    make_student(client, "lti-stale-student@example.com")
    assignment_id = _create_assignment(client, teacher_token)
    student = db_session.query(User).filter_by(email="lti-stale-student@example.com").one()
    platform = _platform(db_session, "stale")
    _mapping(db_session, platform, assignment_id, "stale-resource")
    db_session.add(LTIUserLink(platform_id=platform.id, lti_subject="stale-learner", user_id=student.id))
    db_session.flush()

    access_token = _lti_session(db_session, student, platform, "stale-resource")
    submitted = client.post(
        f"/assignments/{assignment_id}/submit",
        json={"written_answer": "supersede test"},
        headers=auth(access_token),
    )
    assert submitted.status_code == 200, submitted.text
    submission = db_session.get(AssignmentSubmission, submitted.json()["id"])

    first = client.post(
        f"/assignments/{assignment_id}/submissions/{submission.id}/grade",
        json={"grade_percentage": 60, "feedback": "First"},
        headers=auth(teacher_token),
    )
    assert first.status_code == 200, first.text
    older = db_session.query(LTIAGSGradeEvent).filter_by(submission_id=submission.id).one()

    second = client.post(
        f"/assignments/{assignment_id}/submissions/{submission.id}/grade",
        json={"grade_percentage": 95, "feedback": "Latest"},
        headers=auth(teacher_token),
    )
    assert second.status_code == 200, second.text
    events = db_session.query(LTIAGSGradeEvent).filter_by(submission_id=submission.id).order_by(
        LTIAGSGradeEvent.grade_version
    ).all()
    assert len(events) == 2

    calls = []
    async def capture(_platform, _lineitem, payload):
        calls.append(payload)

    monkeypatch.setattr(lti_service_module, "post_lti_ags_score", capture)
    assert asyncio.run(lti_service_module.dispatch_lti_grade_event(db_session, older.id)) is False
    refreshed_older = db_session.get(LTIAGSGradeEvent, older.id)
    assert refreshed_older.status == "superseded"
    assert calls == []

    latest = db_session.get(LTIAGSGradeEvent, events[1].id)
    assert asyncio.run(lti_service_module.dispatch_lti_grade_event(db_session, latest.id)) is True
    assert len(calls) == 1
    assert calls[0]["scoreGiven"] == 95.0
