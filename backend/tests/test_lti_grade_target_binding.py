"""Regression tests for resource-bound AGS passback and delivery ordering."""
import asyncio
import secrets
import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import event as sqlalchemy_event

from app.auth.sessions import create_browser_session
from app.models.auth_session import AuthSession
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.lti import LTIAGSDeliveryLease, LTIAGSGradeEvent, LTIAuthCode, LTIAssignmentLink, LTIPlatform, LTIUserLink
from app.models.user import User, UserRole
from app.services import lti_ags_service as lti_service_module
from app.services.lti_service import hash_opaque_token
from tests.conftest import TestingSessionLocal, engine
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


def _lti_session(db_session, user, platform, resource_link_id, lti_subject=None):
    access_token, _refresh_token, session = create_browser_session(db_session, user)
    session.lti_platform_id = platform.id
    session.lti_deployment_id = platform.deployment_id
    session.lti_resource_link_id = resource_link_id
    session.lti_subject = lti_subject
    db_session.commit()
    return access_token


def test_grade_passback_is_bound_to_exact_resource_link_not_every_mapping(client, db_session, monkeypatch):
    teacher_token = make_teacher(client, db_session, "lti-target-teacher@example.com")
    make_student(client, "lti-target-student@example.com")
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
    access_token = _lti_session(db_session, student, platform, "course-a-resource", lti_subject="learner-a")
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
    make_student(client, "lti-mismatch-student@example.com")
    assignment_id = _create_assignment(client, teacher_token)
    student_user = db_session.query(User).filter_by(email="lti-mismatch-student@example.com").one()
    platform = _platform(db_session, "three")
    _mapping(db_session, platform, assignment_id, "resource-mapped")
    db_session.add(
        LTIUserLink(platform_id=platform.id, lti_subject="learner-mismatch", user_id=student_user.id)
    )
    db_session.flush()

    access_token = _lti_session(db_session, student_user, platform, "resource-not-mapped", lti_subject="learner-mismatch")
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
            lti_subject="verified-subject-77",
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
    assert lti_sessions[0].lti_subject == "verified-subject-77"


def test_ags_retry_reserves_a_new_timestamp_for_each_delivery_attempt(client, db_session, monkeypatch):
    teacher_token = make_teacher(client, db_session, "lti-retry-teacher@example.com")
    make_student(client, "lti-retry-student@example.com")
    assignment_id = _create_assignment(client, teacher_token)
    student = db_session.query(User).filter_by(email="lti-retry-student@example.com").one()
    platform = _platform(db_session, "retry")
    _mapping(db_session, platform, assignment_id, "retry-resource")
    db_session.add(LTIUserLink(platform_id=platform.id, lti_subject="retry-learner", user_id=student.id))
    db_session.flush()

    access_token = _lti_session(
        db_session, student, platform, "retry-resource", lti_subject="retry-learner"
    )
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
    accepted_by_lms = []

    async def fail_once(_platform, _lineitem, payload):
        # The LMS accepts the score, but the response is lost after acceptance.
        # Retrying is therefore intentionally at-least-once, not exactly-once.
        accepted_by_lms.append(dict(payload))
        timestamps.append(payload["timestamp"])
        if len(timestamps) == 1:
            raise TimeoutError("simulated response lost after LMS acceptance")

    monkeypatch.setattr(lti_service_module, "post_lti_ags_score", fail_once)
    # This fixture owns an outer transaction. The simulated HTTP timeout does
    # not abort PostgreSQL, so keep that test transaction intact while the
    # dispatcher records the retry state after its rollback boundary.
    monkeypatch.setattr(db_session, "rollback", lambda: None)
    assert asyncio.run(lti_service_module.dispatch_lti_grade_event(db_session, event_id)) is False

    event = db_session.get(LTIAGSGradeEvent, event_id)
    assert event.status == "pending"
    assert event.attempts == 1
    assert event.last_error == "TimeoutError: AGS delivery failed"
    # A retry must reserve a timestamp later than the uncertain first attempt.
    event.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    async def succeed(_platform, _lineitem, payload):
        accepted_by_lms.append(dict(payload))
        timestamps.append(payload["timestamp"])

    monkeypatch.setattr(lti_service_module, "post_lti_ags_score", succeed)
    assert asyncio.run(lti_service_module.dispatch_lti_grade_event(db_session, event_id)) is True
    assert len(timestamps) == 2
    assert timestamps[1] > timestamps[0]
    assert [item["scoreGiven"] for item in accepted_by_lms] == [76.0, 76.0]
    assert accepted_by_lms[1]["timestamp"] > accepted_by_lms[0]["timestamp"]
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

    access_token = _lti_session(
        db_session, student, platform, "stale-resource", lti_subject="stale-learner"
    )
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


def test_ags_uses_exact_launch_subject_when_local_user_has_multiple_lms_identities(
    client, db_session
):
    teacher_token = make_teacher(client, db_session, "lti-alias-teacher@example.com")
    make_student(client, "lti-alias-student@example.com")
    student = db_session.query(User).filter_by(email="lti-alias-student@example.com").one()
    assignment_id = _create_assignment(client, teacher_token)
    platform = _platform(db_session, "alias")
    mapping = _mapping(db_session, platform, assignment_id, "alias-resource")
    db_session.add_all([
        LTIUserLink(platform_id=platform.id, lti_subject="learner-primary", user_id=student.id),
        LTIUserLink(platform_id=platform.id, lti_subject="learner-alias", user_id=student.id),
    ])
    db_session.flush()

    token = _lti_session(
        db_session, student, platform, "alias-resource", lti_subject="learner-alias"
    )
    submitted = client.post(
        f"/assignments/{assignment_id}/submit",
        json={"written_answer": "subject identity binding"},
        headers=auth(token),
    )
    assert submitted.status_code == 200, submitted.text
    submission_id = submitted.json()["id"]
    submission = db_session.get(AssignmentSubmission, submission_id)
    assert submission.lti_assignment_link_id == mapping.id
    assert submission.lti_subject == "learner-alias"

    graded = client.post(
        f"/assignments/{assignment_id}/submissions/{submission_id}/grade",
        json={"grade_percentage": 88, "feedback": "Correct identity"},
        headers=auth(teacher_token),
    )
    assert graded.status_code == 200, graded.text
    event = db_session.query(LTIAGSGradeEvent).filter_by(submission_id=submission_id).one()
    assert event.lti_subject == "learner-alias"

def test_ags_delivery_uses_per_learner_lease_and_releases_session_transaction(
    client, db_session, monkeypatch
):
    teacher_token = make_teacher(client, db_session, "lti-lease-teacher@example.com")
    make_student(client, "lti-lease-student@example.com")
    assignment_id = _create_assignment(client, teacher_token)
    student = db_session.query(User).filter_by(email="lti-lease-student@example.com").one()
    platform = _platform(db_session, "lease")
    mapping = _mapping(db_session, platform, assignment_id, "lease-resource")
    db_session.add(
        LTIUserLink(platform_id=platform.id, lti_subject="lease-learner", user_id=student.id)
    )
    db_session.flush()

    token = _lti_session(
        db_session, student, platform, "lease-resource", lti_subject="lease-learner"
    )
    submitted = client.post(
        f"/assignments/{assignment_id}/submit",
        json={"written_answer": "delivery lease test"},
        headers=auth(token),
    )
    assert submitted.status_code == 200, submitted.text
    submission_id = submitted.json()["id"]

    graded = client.post(
        f"/assignments/{assignment_id}/submissions/{submission_id}/grade",
        json={"grade_percentage": 60, "feedback": "First grade"},
        headers=auth(teacher_token),
    )
    assert graded.status_code == 200, graded.text
    first = db_session.query(LTIAGSGradeEvent).filter_by(submission_id=submission_id).one()

    latest_event_id = None
    delivered_scores = []

    async def simulate_in_flight_delivery(_platform, _lineitem_url, payload):
        nonlocal latest_event_id
        # The dispatcher must not have an active ORM transaction while waiting
        # for the simulated OAuth/HTTP call.
        assert not db_session.in_transaction()
        delivered_scores.append(payload["scoreGiven"])

        if latest_event_id is None:
            latest = LTIAGSGradeEvent(
                assignment_link_id=mapping.id,
                submission_id=submission_id,
                grade_version=2,
                lti_subject="lease-learner",
                score_given=95,
                score_maximum=100,
                comment="Latest grade",
            )
            db_session.add(latest)
            db_session.commit()
            latest_event_id = latest.id

            # A concurrent worker for the same resource/learner must not start
            # another LMS request until the first request releases its lease.
            assert await lti_service_module.dispatch_lti_grade_event(
                db_session, latest_event_id
            ) is False

    monkeypatch.setattr(lti_service_module, "post_lti_ags_score", simulate_in_flight_delivery)
    assert asyncio.run(lti_service_module.dispatch_lti_grade_event(db_session, first.id)) is True
    assert latest_event_id is not None

    first_after = db_session.get(LTIAGSGradeEvent, first.id)
    latest_after = db_session.get(LTIAGSGradeEvent, latest_event_id)
    assert first_after.status == "sent"
    assert latest_after.status == "pending"

    # Once the first call is complete and the lease is released, the newer
    # grade can be delivered. The external order must be old then latest.
    assert asyncio.run(
        lti_service_module.dispatch_lti_grade_event(db_session, latest_event_id)
    ) is True
    assert delivered_scores == [60.0, 95.0]

    lease = db_session.query(LTIAGSDeliveryLease).filter_by(
        assignment_link_id=mapping.id
    ).one()
    assert lease.owner_token is None
    assert lease.event_id is None
    assert lease.locked_until is None

def test_ags_delivery_lease_blocks_second_independent_database_worker(monkeypatch):
    """Two independent PostgreSQL sessions cannot deliver the same learner/resource concurrently."""
    suffix = secrets.token_hex(8)
    setup = TestingSessionLocal()
    ids = {}
    try:
        teacher = User(
            email=f"lti-lease-worker-teacher-{suffix}@example.test",
            hashed_password="test-only-password-hash",
            role=UserRole.teacher,
        )
        student = User(
            email=f"lti-lease-worker-student-{suffix}@example.test",
            hashed_password="test-only-password-hash",
            role=UserRole.user,
        )
        platform = LTIPlatform(
            name=f"Independent worker sandbox {suffix}",
            issuer=f"https://moodle-workers-{suffix}.example.test",
            client_id=f"client-workers-{suffix}",
            deployment_id=f"deployment-workers-{suffix}",
            auth_login_url=f"https://moodle-workers-{suffix}.example.test/login",
            auth_token_url=f"https://moodle-workers-{suffix}.example.test/token",
            jwks_url=f"https://moodle-workers-{suffix}.example.test/jwks",
        )
        setup.add_all([teacher, student, platform])
        setup.flush()

        assignment = Assignment(
            created_by_user_id=teacher.id,
            title=f"Independent worker lease {suffix}",
            description="Integration-only lease contention fixture",
        )
        setup.add(assignment)
        setup.flush()
        mapping = _mapping(setup, platform, assignment.id, f"resource-{suffix}")
        submission = AssignmentSubmission(
            assignment_id=assignment.id,
            student_user_id=student.id,
            written_answer="lease integration test",
            is_late=False,
            lti_assignment_link_id=mapping.id,
            lti_subject=f"learner-{suffix}",
        )
        setup.add(submission)
        setup.flush()

        now = datetime.now(timezone.utc)
        first = LTIAGSGradeEvent(
            assignment_link_id=mapping.id,
            submission_id=submission.id,
            grade_version=1,
            lti_subject=f"learner-{suffix}",
            score_given=60,
            score_maximum=100,
            status="pending",
            attempts=0,
            next_attempt_at=now,
            score_timestamp=now,
        )
        setup.add(first)
        setup.commit()
        ids = {
            "teacher_id": teacher.id,
            "student_id": student.id,
            "platform_id": platform.id,
            "assignment_id": assignment.id,
            "mapping_id": mapping.id,
            "submission_id": submission.id,
            "first_event_id": first.id,
        }
    finally:
        setup.close()

    worker_one = TestingSessionLocal()
    worker_two = TestingSessionLocal()
    second_event_ids = []
    delivered_scores = []

    async def fake_lms_delivery(_platform, _lineitem_url, payload):
        # The first worker must have released its SQLAlchemy transaction before
        # invoking the external LMS. Its second worker uses a different DB connection.
        assert not worker_one.in_transaction()
        delivered_scores.append(payload["scoreGiven"])

        if not second_event_ids:
            # Simulate a teacher re-grade from a third, independent DB session.
            # The active delivery worker must remain outside a transaction while
            # the external LMS request is waiting.
            grader_session = TestingSessionLocal()
            try:
                later = LTIAGSGradeEvent(
                    assignment_link_id=ids["mapping_id"],
                    submission_id=ids["submission_id"],
                    grade_version=2,
                    lti_subject=f"learner-{suffix}",
                    score_given=95,
                    score_maximum=100,
                    status="pending",
                    attempts=0,
                    next_attempt_at=datetime.now(timezone.utc),
                    score_timestamp=datetime.now(timezone.utc),
                )
                grader_session.add(later)
                grader_session.flush()
                later_event_id = later.id
                grader_session.commit()
            finally:
                grader_session.close()
            second_event_ids.append(later_event_id)

            # This is a different SQLAlchemy Session/connection. It must fail
            # the atomic lease claim while worker one's simulated HTTP call is in flight.
            assert not worker_one.in_transaction()
            assert not worker_two.in_transaction()
            assert await lti_service_module.dispatch_lti_grade_event(
                worker_two, later_event_id
            ) is False
            assert not worker_one.in_transaction()
            assert not worker_two.in_transaction()

    try:
        monkeypatch.setattr(
            lti_service_module, "post_lti_ags_score", fake_lms_delivery
        )
        assert asyncio.run(
            lti_service_module.dispatch_lti_grade_event(
                worker_one, ids["first_event_id"]
            )
        ) is True
        assert len(second_event_ids) == 1

        # After worker one records success and releases the lease, worker two
        # can claim and deliver the latest grade. Delivery order is preserved.
        assert asyncio.run(
            lti_service_module.dispatch_lti_grade_event(
                worker_two, second_event_ids[0]
            )
        ) is True
        assert delivered_scores == [60.0, 95.0]
    finally:
        worker_one.close()
        worker_two.close()
        cleanup = TestingSessionLocal()
        try:
            cleanup.query(LTIAGSDeliveryLease).filter_by(
                assignment_link_id=ids.get("mapping_id", -1)
            ).delete(synchronize_session=False)
            cleanup.query(LTIAGSGradeEvent).filter_by(
                submission_id=ids.get("submission_id", -1)
            ).delete(synchronize_session=False)
            cleanup.query(AssignmentSubmission).filter_by(
                id=ids.get("submission_id", -1)
            ).delete(synchronize_session=False)
            cleanup.query(LTIAssignmentLink).filter_by(
                id=ids.get("mapping_id", -1)
            ).delete(synchronize_session=False)
            cleanup.query(Assignment).filter_by(
                id=ids.get("assignment_id", -1)
            ).delete(synchronize_session=False)
            cleanup.query(LTIPlatform).filter_by(
                id=ids.get("platform_id", -1)
            ).delete(synchronize_session=False)
            user_ids = [
                value for value in (ids.get("teacher_id"), ids.get("student_id"))
                if value is not None
            ]
            if user_ids:
                cleanup.query(User).filter(User.id.in_(user_ids)).delete(
                    synchronize_session=False
                )
            cleanup.commit()
        finally:
            cleanup.close()




def _seed_independent_ags_targets(setup, suffix, count=1):
    """Create committed PostgreSQL rows for worker tests using independent sessions."""
    teacher = User(
        email=f"lti-worker-teacher-{suffix}@example.test",
        hashed_password="test-only-password-hash",
        role=UserRole.teacher,
    )
    student = User(
        email=f"lti-worker-student-{suffix}@example.test",
        hashed_password="test-only-password-hash",
        role=UserRole.user,
    )
    platform = LTIPlatform(
        name=f"Worker lease sandbox {suffix}",
        issuer=f"https://moodle-workers-{suffix}.example.test",
        client_id=f"client-workers-{suffix}",
        deployment_id=f"deployment-workers-{suffix}",
        auth_login_url=f"https://moodle-workers-{suffix}.example.test/login",
        auth_token_url=f"https://moodle-workers-{suffix}.example.test/token",
        jwks_url=f"https://moodle-workers-{suffix}.example.test/jwks",
    )
    setup.add_all([teacher, student, platform])
    setup.flush()

    assignment_ids = []
    mapping_ids = []
    submission_ids = []
    event_ids = []
    for index in range(count):
        assignment = Assignment(
            created_by_user_id=teacher.id,
            title=f"Independent AGS target {suffix}-{index}",
            description="PostgreSQL delivery worker integration test",
        )
        setup.add(assignment)
        setup.flush()
        mapping = _mapping(setup, platform, assignment.id, f"resource-{suffix}-{index}")
        subject = f"learner-{suffix}-{index}"
        submission = AssignmentSubmission(
            assignment_id=assignment.id,
            student_user_id=student.id,
            written_answer="independent AGS worker test",
            is_late=False,
            lti_assignment_link_id=mapping.id,
            lti_subject=subject,
        )
        setup.add(submission)
        setup.flush()
        now = datetime.now(timezone.utc)
        event = LTIAGSGradeEvent(
            assignment_link_id=mapping.id,
            submission_id=submission.id,
            grade_version=1,
            lti_subject=subject,
            score_given=60 + index,
            score_maximum=100,
            status="pending",
            attempts=0,
            next_attempt_at=now,
            score_timestamp=now,
        )
        setup.add(event)
        setup.flush()
        assignment_ids.append(assignment.id)
        mapping_ids.append(mapping.id)
        submission_ids.append(submission.id)
        event_ids.append(event.id)

    setup.commit()
    return {
        "teacher_id": teacher.id,
        "student_id": student.id,
        "platform_id": platform.id,
        "assignment_ids": assignment_ids,
        "mapping_ids": mapping_ids,
        "submission_ids": submission_ids,
        "event_ids": event_ids,
    }


def _cleanup_independent_ags_targets(ids):
    cleanup = TestingSessionLocal()
    try:
        mapping_ids = ids.get("mapping_ids", [])
        event_ids = ids.get("event_ids", [])
        submission_ids = ids.get("submission_ids", [])
        assignment_ids = ids.get("assignment_ids", [])
        if mapping_ids:
            cleanup.query(LTIAGSDeliveryLease).filter(
                LTIAGSDeliveryLease.assignment_link_id.in_(mapping_ids)
            ).delete(synchronize_session=False)
        if event_ids:
            cleanup.query(LTIAGSGradeEvent).filter(
                LTIAGSGradeEvent.id.in_(event_ids)
            ).delete(synchronize_session=False)
        if submission_ids:
            cleanup.query(AssignmentSubmission).filter(
                AssignmentSubmission.id.in_(submission_ids)
            ).delete(synchronize_session=False)
        if mapping_ids:
            cleanup.query(LTIAssignmentLink).filter(
                LTIAssignmentLink.id.in_(mapping_ids)
            ).delete(synchronize_session=False)
        if assignment_ids:
            cleanup.query(Assignment).filter(
                Assignment.id.in_(assignment_ids)
            ).delete(synchronize_session=False)
        if ids.get("platform_id") is not None:
            cleanup.query(LTIPlatform).filter(
                LTIPlatform.id == ids["platform_id"]
            ).delete(synchronize_session=False)
        user_ids = [
            value for value in (ids.get("teacher_id"), ids.get("student_id"))
            if value is not None
        ]
        if user_ids:
            cleanup.query(User).filter(User.id.in_(user_ids)).delete(
                synchronize_session=False
            )
        cleanup.commit()
    finally:
        cleanup.close()


def test_ags_expired_lease_is_reclaimed_and_stale_worker_is_fenced(monkeypatch):
    """An expired owner can be replaced; its late completion cannot finalize the event."""
    suffix = secrets.token_hex(8)
    setup = TestingSessionLocal()
    ids = {}
    try:
        ids = _seed_independent_ags_targets(setup, suffix, count=1)
    finally:
        setup.close()

    worker_one = TestingSessionLocal()
    worker_two = TestingSessionLocal()
    attempts = []
    old_owner = None
    event_id = ids["event_ids"][0]
    mapping_id = ids["mapping_ids"][0]

    async def fake_lms_delivery(_platform, _lineitem_url, payload):
        nonlocal old_owner
        attempts.append(dict(payload))
        assert not worker_one.in_transaction()
        assert not worker_two.in_transaction()

        if len(attempts) == 1:
            observer = TestingSessionLocal()
            try:
                lease = observer.query(LTIAGSDeliveryLease).filter_by(
                    assignment_link_id=mapping_id
                ).one()
                old_owner = lease.owner_token
                assert old_owner
                # Model a worker that stopped making progress after its durable
                # claim. The next worker may recover only after both lease views expire.
                expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                lease.locked_until = expired_at
                event = observer.get(LTIAGSGradeEvent, event_id)
                event.locked_until = expired_at
                observer.commit()
            finally:
                observer.close()

            # A second independent PostgreSQL session reclaims the expired lease
            # and completes the same at-least-once delivery.
            assert await lti_service_module.dispatch_lti_grade_event(
                worker_two, event_id
            ) is True
            return

        observer = TestingSessionLocal()
        try:
            lease = observer.query(LTIAGSDeliveryLease).filter_by(
                assignment_link_id=mapping_id
            ).one()
            assert lease.owner_token
            assert lease.owner_token != old_owner
        finally:
            observer.close()

    try:
        monkeypatch.setattr(
            lti_service_module, "post_lti_ags_score", fake_lms_delivery
        )
        # Worker one resumes after worker two has taken over. It must not
        # overwrite the newer owner's successful finalization.
        assert asyncio.run(
            lti_service_module.dispatch_lti_grade_event(worker_one, event_id)
        ) is False
        assert len(attempts) == 2
        assert attempts[1]["timestamp"] > attempts[0]["timestamp"]

        verify = TestingSessionLocal()
        try:
            event = verify.get(LTIAGSGradeEvent, event_id)
            lease = verify.query(LTIAGSDeliveryLease).filter_by(
                assignment_link_id=mapping_id
            ).one()
            assert event.status == "sent"
            assert event.attempts == 2
            assert event.delivered_at is not None
            assert lease.owner_token is None
            assert lease.event_id is None
            assert lease.locked_until is None
        finally:
            verify.close()
    finally:
        worker_one.close()
        worker_two.close()
        _cleanup_independent_ags_targets(ids)


def test_ags_concurrent_targets_release_all_db_pool_connections_during_lms_io(monkeypatch):
    """Concurrent deliveries to distinct targets must not pin PostgreSQL pool connections."""
    suffix = secrets.token_hex(8)
    setup = TestingSessionLocal()
    ids = {}
    try:
        ids = _seed_independent_ags_targets(setup, suffix, count=6)
    finally:
        setup.close()

    workers = [TestingSessionLocal() for _ in ids["event_ids"]]
    all_started = asyncio.Event()
    release_network = asyncio.Event()
    waiting = 0

    async def blocked_lms_delivery(_platform, _lineitem_url, _payload):
        nonlocal waiting
        assert all(not worker.in_transaction() for worker in workers)
        waiting += 1
        if waiting == len(workers):
            # Every worker is paused in the simulated network call. No worker
            # should still hold a checked-out connection from the SQLAlchemy pool.
            assert engine.pool.checkedout() == 0
            all_started.set()
        await release_network.wait()

    async def run_concurrent_deliveries():
        tasks = [
            asyncio.create_task(
                lti_service_module.dispatch_lti_grade_event(worker, event_id)
            )
            for worker, event_id in zip(workers, ids["event_ids"])
        ]
        await asyncio.wait_for(all_started.wait(), timeout=10)
        assert engine.pool.checkedout() == 0
        release_network.set()
        return await asyncio.gather(*tasks)

    try:
        monkeypatch.setattr(
            lti_service_module, "post_lti_ags_score", blocked_lms_delivery
        )
        assert asyncio.run(run_concurrent_deliveries()) == [True] * len(workers)
        assert engine.pool.checkedout() == 0
    finally:
        for worker in workers:
            worker.close()
        _cleanup_independent_ags_targets(ids)


def test_ags_exhausted_crash_recovery_requires_one_admin_authorized_retry(
    client, db_session, monkeypatch
):
    suffix = secrets.token_hex(6)
    admin = User(
        email=f"lti-ags-retry-admin-{suffix}@example.test",
        hashed_password="test-only-password-hash",
        role=UserRole.admin,
    )
    student = User(
        email=f"lti-ags-retry-student-{suffix}@example.test",
        hashed_password="test-only-password-hash",
        role=UserRole.user,
    )
    db_session.add_all([admin, student])
    db_session.flush()
    admin_token, _refresh_token, _auth_session = create_browser_session(db_session, admin)

    assignment = Assignment(
        created_by_user_id=admin.id,
        title=f"AGS retry-cap {suffix}",
        description="Regression for admin-authorized delivery retry",
    )
    db_session.add(assignment)
    db_session.flush()
    platform = _platform(db_session, f"retry-{suffix}")
    mapping = _mapping(db_session, platform, assignment.id, f"retry-resource-{suffix}")
    now = datetime.now(timezone.utc)
    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        student_user_id=student.id,
        written_answer="AGS retry-cap regression",
        is_late=False,
        grade_version=1,
        lti_assignment_link_id=mapping.id,
        lti_subject=f"learner-{suffix}",
    )
    db_session.add(submission)
    db_session.flush()
    event = LTIAGSGradeEvent(
        assignment_link_id=mapping.id,
        submission_id=submission.id,
        grade_version=1,
        lti_subject=submission.lti_subject,
        score_given=80,
        score_maximum=100,
        status="pending",
        attempts=lti_service_module.AGS_MAX_DELIVERY_ATTEMPTS,
        next_attempt_at=now - timedelta(minutes=1),
        score_timestamp=now - timedelta(minutes=5),
        locked_until=now - timedelta(seconds=1),
    )
    db_session.add(event)
    db_session.commit()

    unexpected_calls = []

    async def unexpected_delivery(*_args, **_kwargs):
        unexpected_calls.append(True)

    monkeypatch.setattr(
        lti_service_module, "post_lti_ags_score", unexpected_delivery
    )
    assert asyncio.run(
        lti_service_module.dispatch_lti_grade_event(db_session, event.id)
    ) is False
    db_session.refresh(event)
    assert event.status == "dead"
    assert event.attempts == lti_service_module.AGS_MAX_DELIVERY_ATTEMPTS
    assert event.manual_retry_requested_at is None
    assert unexpected_calls == []

    retry_response = client.post(
        f"/lti/grade-events/{event.id}/retry",
        headers=auth(admin_token),
    )
    assert retry_response.status_code == 200, retry_response.text
    db_session.refresh(event)
    assert event.status == "pending"
    assert event.manual_retry_requested_at is not None

    delivered = []

    async def accepted_delivery(_platform, _lineitem_url, score):
        delivered.append(score)

    monkeypatch.setattr(
        lti_service_module, "post_lti_ags_score", accepted_delivery
    )
    assert asyncio.run(
        lti_service_module.dispatch_lti_grade_event(db_session, event.id)
    ) is True
    db_session.refresh(event)
    assert len(delivered) == 1
    assert event.status == "sent"
    assert event.attempts == lti_service_module.AGS_MAX_DELIVERY_ATTEMPTS + 1
    assert event.manual_retry_requested_at is None


def test_ags_retry_waits_for_uncommitted_regrade_before_reserving_timestamp(monkeypatch):
    """A retry must wait on the submission lock, then supersede an uncommitted newer grade."""
    if engine.dialect.name != "postgresql":
        import pytest
        pytest.skip("Requires PostgreSQL row-level FOR UPDATE semantics")

    suffix = secrets.token_hex(8)
    setup = TestingSessionLocal()
    ids = {}
    try:
        ids = _seed_independent_ags_targets(setup, suffix, count=1)
        old_event = setup.get(LTIAGSGradeEvent, ids["event_ids"][0])
        old_timestamp = datetime.now(timezone.utc) - timedelta(minutes=5)
        old_event.attempts = 1
        old_event.score_timestamp = old_timestamp
        old_event.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        old_event.locked_until = None
        setup.commit()
    finally:
        setup.close()

    grader = TestingSessionLocal()
    lock_query_started = threading.Event()
    worker_result = {}
    worker_errors = []
    network_calls = []
    listener = None
    worker = None

    try:
        submission = (
            grader.query(AssignmentSubmission)
            .filter(AssignmentSubmission.id == ids["submission_ids"][0])
            .with_for_update()
            .one()
        )
        assignment = grader.get(Assignment, ids["assignment_ids"][0])
        grader.add(
            LTIUserLink(
                platform_id=ids["platform_id"],
                lti_subject=submission.lti_subject,
                user_id=ids["student_id"],
            )
        )
        grader.flush()
        submission.grade_version = 2
        submission.grade_percentage = 95
        submission.feedback = "Concurrent re-grade"
        submission.graded_at = old_timestamp + timedelta(microseconds=2)
        new_event_id = lti_service_module.create_lti_ags_grade_event(
            grader, assignment, submission
        )
        assert new_event_id is not None
        grader.flush()

        def before_cursor_execute(
            _connection, _cursor, statement, _parameters, _context, _executemany
        ):
            normalized = statement.lower()
            if "assignment_submissions" in normalized and "for update" in normalized:
                lock_query_started.set()

        listener = before_cursor_execute
        sqlalchemy_event.listen(engine, "before_cursor_execute", listener)

        async def should_not_deliver(*_args, **_kwargs):
            network_calls.append(True)

        monkeypatch.setattr(
            lti_service_module, "post_lti_ags_score", should_not_deliver
        )

        def run_dispatch():
            worker_session = TestingSessionLocal()
            try:
                worker_result["result"] = asyncio.run(
                    lti_service_module.dispatch_lti_grade_event(
                        worker_session, ids["event_ids"][0]
                    )
                )
            except BaseException as exc:
                worker_errors.append(exc)
            finally:
                worker_session.close()

        worker = threading.Thread(target=run_dispatch, daemon=True)
        worker.start()
        assert lock_query_started.wait(timeout=5), (
            "dispatcher did not request the submission row lock before retry timestamp reservation"
        )

        # The dispatcher is waiting on the row lock held by the re-grade transaction.
        # Commit the newer grade; the retry must observe it and stop before network I/O.
        grader.commit()
        ids["event_ids"].append(new_event_id)
        worker.join(timeout=10)
        assert not worker.is_alive(), "dispatcher remained blocked after the re-grade committed"
        assert not worker_errors, repr(worker_errors)
        assert worker_result.get("result") is False
        assert network_calls == []

        verify = TestingSessionLocal()
        try:
            old_after = verify.get(LTIAGSGradeEvent, ids["event_ids"][0])
            new_after = verify.get(LTIAGSGradeEvent, new_event_id)
            assert old_after.status == "superseded"
            assert old_after.score_timestamp == old_timestamp
            assert new_after.status == "pending"
            assert new_after.score_timestamp == old_timestamp + timedelta(microseconds=2)
        finally:
            verify.close()
    finally:
        if worker is not None:
            worker.join(timeout=2)
        if listener is not None:
            sqlalchemy_event.remove(engine, "before_cursor_execute", listener)
        if grader.in_transaction():
            grader.rollback()
        grader.close()
        _cleanup_independent_ags_targets(ids)
