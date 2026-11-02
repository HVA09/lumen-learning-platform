"""Protocol-level tests for LTI AGS mappings, grade outbox, OAuth and score delivery."""
import asyncio
from datetime import datetime, timedelta, timezone
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from types import SimpleNamespace
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from app.models.assignment import Assignment, AssignmentSubmission
from app.models.lti import (
    LTIAGSGradeEvent, LTIAssignmentLink, LTIPlatform, LTIUserLink,
    LTIResourceLinkDiscovery,
)
from app.models.user import User, UserRole
from app.services import lti_service
from app.services.lti_service import (
    AGS_ENDPOINT_CLAIM,
    AGS_RESOURCE_LINK_CLAIM,
    AGS_SCORE_SCOPE,
    build_ags_client_assertion,
    dispatch_lti_grade_event,
    record_lti_ags_launch_context,
)
from tests.quiz_helpers import auth, make_student, make_teacher, register_and_login, set_role


def _platform(db_session):
    platform = LTIPlatform(
        name="Moodle AGS Test",
        issuer="https://moodle.example.test",
        client_id="lumen-test-client",
        deployment_id="moodle-deploy-1",
        auth_login_url="https://moodle.example.test/mod/lti/auth.php",
        auth_token_url="https://moodle.example.test/mod/lti/token.php",
        jwks_url="https://moodle.example.test/mod/lti/certs.php",
    )
    db_session.add(platform)
    db_session.flush()
    return platform


def _make_pending_event(client, db_session, *, grade=84.0):
    teacher_token = make_teacher(client, db_session, "ags-teacher@example.com")
    student_token = make_student(client, "ags-student@example.com")
    assignment_response = client.post(
        "/assignments",
        json={"title": "AGS assignment", "description": "Grade passback test"},
        headers=auth(teacher_token),
    )
    assert assignment_response.status_code == 201, assignment_response.text
    assignment = db_session.get(Assignment, assignment_response.json()["id"])
    platform = _platform(db_session)
    mapping = LTIAssignmentLink(
        platform_id=platform.id,
        assignment_id=assignment.id,
        deployment_id=platform.deployment_id,
        resource_link_id="lms-resource-ags-1",
        lineitem_url="https://moodle.example.test/mod/lti/lineitems/42?tenant=ags-v1",
        score_scope_allowed=True,
        score_maximum=100.0,
    )
    student = db_session.query(User).filter(User.email == "ags-student@example.com").one()
    db_session.add(mapping)
    db_session.add(
        LTIUserLink(
            platform_id=platform.id,
            lti_subject="moodle-subject-42",
            user_id=student.id,
        )
    )
    db_session.commit()

    submitted = client.post(
        f"/assignments/{assignment.id}/submit",
        json={"written_answer": "A valid written answer."},
        headers=auth(student_token),
    )
    assert submitted.status_code == 200, submitted.text
    graded = client.post(
        f"/assignments/{assignment.id}/submissions/{submitted.json()['id']}/grade",
        json={"grade_percentage": grade, "feedback": "Good work"},
        headers=auth(teacher_token),
    )
    assert graded.status_code == 200, graded.text
    event = (
        db_session.query(LTIAGSGradeEvent)
        .filter(LTIAGSGradeEvent.submission_id == submitted.json()["id"])
        .one()
    )
    return platform, mapping, event


def test_assignment_link_is_admin_only_and_unique(client, db_session):
    teacher = make_teacher(client, db_session, "ags-map-teacher@example.com")
    assignment = client.post(
        "/assignments",
        json={"title": "Mapped assignment", "description": "For LTI"},
        headers=auth(teacher),
    ).json()
    admin_token = register_and_login(client, "ags-map-admin@example.com")
    set_role(db_session, "ags-map-admin@example.com", UserRole.admin)
    platform = _platform(db_session)
    payload = {
        "platform_id": platform.id,
        "assignment_id": assignment["id"],
        "resource_link_id": "lms-resource-1",
        "score_maximum": 25.0,
    }

    denied = client.post("/lti/assignment-links", json=payload, headers=auth(teacher))
    assert denied.status_code == 403

    created = client.post("/lti/assignment-links", json=payload, headers=auth(admin_token))
    assert created.status_code == 201, created.text
    assert created.json()["lineitem_ready"] is False
    assert created.json()["score_maximum"] == 25.0

    duplicate = client.post("/lti/assignment-links", json=payload, headers=auth(admin_token))
    assert duplicate.status_code == 409


def test_unmapped_resource_link_is_discovered_admin_only_and_prefills_mapping(
    client, db_session
):
    teacher_token = make_teacher(client, db_session, "ags-discovery-teacher@example.com")
    assignment_response = client.post(
        "/assignments",
        json={"title": "Discoverable assignment", "description": "Sandbox mapping"},
        headers=auth(teacher_token),
    )
    assert assignment_response.status_code == 201, assignment_response.text

    admin_token = register_and_login(client, "ags-discovery-admin@example.com")
    set_role(db_session, "ags-discovery-admin@example.com", UserRole.admin)
    platform = _platform(db_session)
    claims = {
        AGS_RESOURCE_LINK_CLAIM: {"id": "new-lms-resource-9"},
        AGS_ENDPOINT_CLAIM: {
            "lineitem": "https://moodle.example.test/mod/lti/lineitems/9?tenant=discovery",
            "scope": [AGS_SCORE_SCOPE],
        },
    }

    assert record_lti_ags_launch_context(db_session, platform, claims) is True
    db_session.commit()

    discovery = (
        db_session.query(LTIResourceLinkDiscovery)
        .filter(LTIResourceLinkDiscovery.resource_link_id == "new-lms-resource-9")
        .one()
    )
    assert discovery.lineitem_ready is True

    denied = client.get("/lti/resource-links", headers=auth(teacher_token))
    assert denied.status_code == 403

    observed = client.get("/lti/resource-links", headers=auth(admin_token))
    assert observed.status_code == 200, observed.text
    row = next(
        item for item in observed.json()
        if item["resource_link_id"] == "new-lms-resource-9"
    )
    assert row["lineitem_ready"] is True
    assert row["score_scope_allowed"] is True
    assert row["mapped_assignment_id"] is None
    assert "lti_subject" not in row
    assert "lineitem_url" not in row

    created = client.post(
        "/lti/assignment-links",
        json={
            "platform_id": platform.id,
            "assignment_id": assignment_response.json()["id"],
            "resource_link_id": "new-lms-resource-9",
            "score_maximum": 25.0,
        },
        headers=auth(admin_token),
    )
    assert created.status_code == 201, created.text
    assert created.json()["lineitem_ready"] is True
    assert created.json()["score_scope_allowed"] is True
    assert created.json()["score_maximum"] == 25.0

    db_mapping = db_session.get(LTIAssignmentLink, created.json()["id"])
    assert db_mapping.lineitem_url.endswith("?tenant=discovery")


def test_resource_link_discovery_upsert_is_idempotent_and_refreshes_mapping(db_session):
    platform = _platform(db_session)
    owner = User(email="ags-upsert-owner@example.com", hashed_password="not-used")
    db_session.add(owner)
    db_session.flush()
    assignment = Assignment(
        created_by_user_id=owner.id,
        title="Upsert mapping",
        description="Concurrent first launches",
    )
    db_session.add(assignment)
    db_session.flush()
    mapping = LTIAssignmentLink(
        platform_id=platform.id,
        assignment_id=assignment.id,
        deployment_id=platform.deployment_id,
        resource_link_id="resource-upsert-1",
    )
    db_session.add(mapping)
    db_session.flush()

    first_claims = {
        AGS_RESOURCE_LINK_CLAIM: {"id": "resource-upsert-1"},
        AGS_ENDPOINT_CLAIM: {
            "lineitem": "https://moodle.example.test/mod/lti/lineitems/11",
            "scope": [AGS_SCORE_SCOPE],
        },
    }
    assert record_lti_ags_launch_context(db_session, platform, first_claims) is True
    db_session.flush()

    discovery = (
        db_session.query(LTIResourceLinkDiscovery)
        .filter(
            LTIResourceLinkDiscovery.platform_id == platform.id,
            LTIResourceLinkDiscovery.resource_link_id == "resource-upsert-1",
        )
        .one()
    )
    original_first_seen = discovery.first_seen_at
    discovery.first_seen_at = original_first_seen.replace(year=original_first_seen.year - 1)
    expected_first_seen = discovery.first_seen_at
    db_session.flush()

    refreshed_claims = {
        AGS_RESOURCE_LINK_CLAIM: {"id": "resource-upsert-1"},
        AGS_ENDPOINT_CLAIM: {
            "lineitem": "https://moodle.example.test/mod/lti/lineitems/12?tenant=updated",
            "scope": [AGS_SCORE_SCOPE],
        },
    }
    assert record_lti_ags_launch_context(db_session, platform, refreshed_claims) is True
    db_session.flush()
    db_session.refresh(discovery)
    db_session.refresh(mapping)

    discoveries = (
        db_session.query(LTIResourceLinkDiscovery)
        .filter(
            LTIResourceLinkDiscovery.platform_id == platform.id,
            LTIResourceLinkDiscovery.resource_link_id == "resource-upsert-1",
        )
        .all()
    )
    assert len(discoveries) == 1
    assert discovery.first_seen_at == expected_first_seen
    assert discovery.lineitem_url.endswith("/lineitems/12?tenant=updated")
    assert discovery.score_scope_allowed is True
    assert mapping.lineitem_url == discovery.lineitem_url
    assert mapping.score_scope_allowed is True


def test_launch_context_requires_score_scope_and_same_platform_origin(db_session):
    platform = _platform(db_session)
    # Use a real user row for the assignment foreign key.
    owner = User(email="ags-owner@example.com", hashed_password="not-used")
    db_session.add(owner)
    db_session.flush()
    assignment = Assignment(
        created_by_user_id=owner.id,
        title="Launch mapping",
        description="Test",
    )
    db_session.add(assignment)
    db_session.flush()
    mapping = LTIAssignmentLink(
        platform_id=platform.id,
        assignment_id=assignment.id,
        deployment_id=platform.deployment_id,
        resource_link_id="resource-from-launch",
    )
    db_session.add(mapping)
    db_session.flush()

    base_claims = {
        AGS_RESOURCE_LINK_CLAIM: {"id": "resource-from-launch"},
        AGS_ENDPOINT_CLAIM: {
            "lineitem": "https://moodle.example.test/mod/lti/lineitems/7?tenant=ags-v1",
            "scope": [AGS_SCORE_SCOPE],
        },
    }
    assert record_lti_ags_launch_context(db_session, platform, base_claims) is True
    assert mapping.lineitem_ready is True
    assert mapping.lineitem_url.endswith("?tenant=ags-v1")

    wrong_origin = {
        **base_claims,
        AGS_ENDPOINT_CLAIM: {
            "lineitem": "https://attacker.example.test/collect/scores",
            "scope": [AGS_SCORE_SCOPE],
        },
    }
    record_lti_ags_launch_context(db_session, platform, wrong_origin)
    assert mapping.lineitem_url is None
    assert mapping.score_scope_allowed is False

    no_score_scope = {
        **base_claims,
        AGS_ENDPOINT_CLAIM: {
            "lineitem": "https://moodle.example.test/mod/lti/lineitems/7",
            "scope": ["https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly"],
        },
    }
    record_lti_ags_launch_context(db_session, platform, no_score_scope)
    assert mapping.lineitem_ready is False


def test_teacher_grading_creates_one_outbox_event_per_grade_version(client, db_session):
    _platform_obj, _mapping, first_event = _make_pending_event(client, db_session, grade=84.0)
    assert first_event.status == "pending"
    assert first_event.grade_version == 1
    assert first_event.lti_subject == "moodle-subject-42"
    assert first_event.score_given == 84.0
    assert first_event.score_maximum == 100.0
    assert first_event.comment == "Good work"

    submission = db_session.get(AssignmentSubmission, first_event.submission_id)
    # Only the original assignment creator can grade; use that account again.
    teacher_token = auth(register_and_login(client, "ags-teacher@example.com"))
    second = client.post(
        f"/assignments/{submission.assignment_id}/submissions/{submission.id}/grade",
        json={"grade_percentage": 91, "feedback": "Regraded"},
        headers=teacher_token,
    )
    assert second.status_code == 200, second.text
    events = (
        db_session.query(LTIAGSGradeEvent)
        .filter(LTIAGSGradeEvent.submission_id == submission.id)
        .order_by(LTIAGSGradeEvent.grade_version)
        .all()
    )
    assert [event.grade_version for event in events] == [1, 2]
    assert [event.score_given for event in events] == [84.0, 91.0]


def test_grade_event_manual_retry_is_admin_only_and_resets_dead_event(client, db_session):
    from datetime import datetime, timedelta, timezone

    _platform_obj, _mapping, event = _make_pending_event(client, db_session)

    teacher_token = make_teacher(client, db_session, "ags-retry-teacher@example.com")
    denied = client.post(
        f"/lti/grade-events/{event.id}/retry",
        headers=auth(teacher_token),
    )
    assert denied.status_code == 403

    admin_email = "ags-retry-admin@example.com"
    admin_token = register_and_login(client, admin_email)
    set_role(db_session, admin_email, UserRole.admin)

    # A pending event cannot be manually retried; this endpoint is for dead letters.
    pending_retry = client.post(
        f"/lti/grade-events/{event.id}/retry",
        headers=auth(admin_token),
    )
    assert pending_retry.status_code == 409

    event.status = "dead"
    event.attempts = 8
    event.last_error = "RuntimeError: AGS delivery failed"
    event.locked_until = datetime.now(timezone.utc) + timedelta(minutes=2)
    event.next_attempt_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db_session.commit()

    retried = client.post(
        f"/lti/grade-events/{event.id}/retry",
        headers=auth(admin_token),
    )
    assert retried.status_code == 200, retried.text
    body = retried.json()
    assert body["id"] == event.id
    assert body["status"] == "pending"
    assert body["attempts"] == 0
    assert body["last_error"] is None

    db_session.refresh(event)
    assert event.status == "pending"
    assert event.attempts == 0
    assert event.last_error is None
    assert event.locked_until is None
    assert event.next_attempt_at <= datetime.now(timezone.utc)


def test_admin_grade_event_list_omits_learner_and_delivery_secrets(client, db_session):
    _platform_obj, _mapping, event = _make_pending_event(client, db_session)
    admin_email = "ags-privacy-admin@example.com"
    admin_token = register_and_login(client, admin_email)
    set_role(db_session, admin_email, UserRole.admin)

    response = client.get("/lti/grade-events", headers=auth(admin_token))
    assert response.status_code == 200, response.text
    row = next(item for item in response.json() if item["id"] == event.id)

    assert row["status"] == "pending"
    forbidden_fields = {
        "lti_subject",
        "score_given",
        "score_maximum",
        "comment",
        "lineitem_url",
        "access_token",
        "client_assertion",
    }
    assert forbidden_fields.isdisjoint(row)
    assert "moodle-subject-42" not in response.text
    assert "tenant=ags-v1" not in response.text


def test_ags_client_assertion_has_short_lived_platform_client_claims(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(lti_service.settings, "LTI_TOOL_PRIVATE_KEY", private_pem)
    monkeypatch.setattr(lti_service.settings, "LTI_TOOL_KID", "lumen-test-kid")
    platform = SimpleNamespace(
        client_id="client-123",
        auth_token_url="https://moodle.example.test/token",
    )

    assertion = build_ags_client_assertion(platform, now=1_800_000_000)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    claims = jwt.decode(
        assertion,
        public_pem,
        algorithms=["RS256"],
        audience=platform.auth_token_url,
    )
    assert claims["iss"] == "client-123"
    assert claims["sub"] == "client-123"
    assert claims["iat"] == 1_800_000_000
    assert claims["exp"] - claims["iat"] == 300
    assert claims["jti"]
    assert jwt.get_unverified_header(assertion)["kid"] == "lumen-test-kid"


def test_ags_outbox_dispatch_posts_signed_token_and_score(client, db_session, monkeypatch):
    platform, _mapping, event = _make_pending_event(client, db_session)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(lti_service.settings, "LTI_TOOL_PRIVATE_KEY", private_pem)
    monkeypatch.setattr(lti_service.settings, "LTI_TOOL_KID", "lumen-test-kid")

    async def fake_resolve(url, **kwargs):
        parsed = urlsplit(url)
        return (
            f"https://93.184.216.34{parsed.path}"
            + (f"?{parsed.query}" if parsed.query else ""),
            {"Host": parsed.netloc},
            {"sni_hostname": parsed.hostname},
        )

    monkeypatch.setattr(lti_service, "resolve_lti_platform_endpoint_url", fake_resolve)
    calls = []

    class FakeResponse:
        def __init__(self, status_code, body):
            self.status_code = status_code
            self.body = body

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("upstream internal detail must not be persisted")

        async def aiter_bytes(self):
            if self.body:
                yield self.body

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            self.options = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            if url.endswith("/token.php"):
                return FakeResponse(200, b'{"access_token":"mock-access","token_type":"Bearer"}')
            return FakeResponse(201, b"{}")

    monkeypatch.setattr(lti_service.httpx, "AsyncClient", FakeAsyncClient)
    delivered = asyncio.run(dispatch_lti_grade_event(db_session, event.id))
    assert delivered is True
    db_session.refresh(event)
    assert event.status == "sent"
    assert event.attempts == 1
    assert event.delivered_at is not None
    assert len(calls) == 2

    token_method, token_url, token_kwargs = calls[0]
    assert token_method == "POST"
    assert token_url.endswith("/token.php")
    assertion = token_kwargs["data"]["client_assertion"]
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    assertion_claims = jwt.decode(
        assertion, public_pem, algorithms=["RS256"], audience=platform.auth_token_url
    )
    assert assertion_claims["sub"] == platform.client_id
    assert token_kwargs["data"]["scope"] == AGS_SCORE_SCOPE

    score_method, score_url, score_kwargs = calls[1]
    assert score_method == "POST"
    assert score_url.endswith("/lineitems/42/scores?tenant=ags-v1")
    assert score_kwargs["headers"]["Authorization"] == "Bearer mock-access"
    score = score_kwargs["json"]
    assert score["userId"] == "moodle-subject-42"
    assert score["scoreGiven"] == 84.0
    assert score["scoreMaximum"] == 100.0
    assert score["activityProgress"] == "Completed"
    assert score["gradingProgress"] == "FullyGraded"
    assert score["comment"] == "Good work"


def test_ags_dispatch_skips_event_with_active_delivery_lease(client, db_session, monkeypatch):
    _platform_obj, _mapping, event = _make_pending_event(client, db_session)
    now = datetime.now(timezone.utc)
    event.locked_until = now + timedelta(minutes=2)
    db_session.commit()

    async def unexpected_delivery(*_args, **_kwargs):
        raise AssertionError("An actively leased grade event must not be delivered twice")

    monkeypatch.setattr(lti_service, "post_lti_ags_score", unexpected_delivery)

    delivered = asyncio.run(dispatch_lti_grade_event(db_session, event.id))
    assert delivered is False

    db_session.refresh(event)
    assert event.status == "pending"
    assert event.attempts == 0
    assert event.locked_until is not None
    assert event.locked_until > now


def test_ags_delivery_moves_event_to_dead_after_max_attempts(client, db_session, monkeypatch):
    _platform_obj, _mapping, event = _make_pending_event(client, db_session)
    event.attempts = lti_service.AGS_MAX_DELIVERY_ATTEMPTS - 1
    db_session.commit()

    async def fail_delivery(*_args, **_kwargs):
        raise RuntimeError("upstream private response details")

    monkeypatch.setattr(lti_service, "post_lti_ags_score", fail_delivery)

    delivered = asyncio.run(dispatch_lti_grade_event(db_session, event.id))
    assert delivered is False

    db_session.refresh(event)
    assert event.status == "dead"
    assert event.attempts == lti_service.AGS_MAX_DELIVERY_ATTEMPTS
    assert event.locked_until is None
    assert event.last_error == "RuntimeError: AGS delivery failed"
    assert "upstream private response details" not in event.last_error


def test_ags_delivery_failure_is_retried_without_persisting_remote_details(client, db_session, monkeypatch):
    _platform_obj, _mapping, event = _make_pending_event(client, db_session)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(lti_service.settings, "LTI_TOOL_PRIVATE_KEY", private_pem)

    async def fake_resolve(url, **kwargs):
        parsed = urlsplit(url)
        return (
            f"https://93.184.216.34{parsed.path}",
            {"Host": parsed.netloc},
            {"sni_hostname": parsed.hostname},
        )

    monkeypatch.setattr(lti_service, "resolve_lti_platform_endpoint_url", fake_resolve)

    class FailingResponse:
        status_code = 503

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            raise RuntimeError("secret upstream diagnostics")

        async def aiter_bytes(self):
            yield b'{"internal":"secret upstream diagnostics"}'

    class FailingAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, method, url, **kwargs):
            return FailingResponse()

    monkeypatch.setattr(lti_service.httpx, "AsyncClient", FailingAsyncClient)
    delivered = asyncio.run(dispatch_lti_grade_event(db_session, event.id))
    assert delivered is False
    db_session.refresh(event)
    assert event.status == "pending"
    assert event.attempts == 1
    assert event.next_attempt_at is not None
    assert "secret upstream diagnostics" not in (event.last_error or "")
    assert "AGS delivery failed" in event.last_error


def test_lti_key_generator_outputs_dotenv_compatible_private_key(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "generate_lti_key.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        check=True,
        capture_output=True,
        text=True,
    )
    env_file = tmp_path / ".env"
    env_file.write_text(completed.stdout, encoding="utf-8")

    generated = dotenv_values(env_file)
    private_pem = generated["LTI_TOOL_PRIVATE_KEY"]
    assert generated["LTI_TOOL_KID"] == "lumen-key-1"
    key = serialization.load_pem_private_key(private_pem.encode("ascii"), password=None)
    assert isinstance(key, rsa.RSAPrivateKey)
    assert key.key_size >= 2048
