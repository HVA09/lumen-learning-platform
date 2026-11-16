"""Regression tests for the one-time first-administrator bootstrap."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.ops.promote_initial_admin import (
    _ADMIN_BOOTSTRAP_LOCK_ID,
    _ADMIN_BOOTSTRAP_LOCK_NAMESPACE,
    promote_initial_admin,
)


def _add_user(db_session, email, *, verified=True, active=True, role=UserRole.user):
    user = User(
        email=email,
        hashed_password="not-used-in-these-tests",
        role=role,
        is_active=active,
        is_email_verified=verified,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_bootstrap_promotes_only_existing_verified_active_user(db_session):
    user = _add_user(db_session, "first-admin-success@example.com")

    promote_initial_admin(
        db_session,
        "first-admin-success@example.com",
        "first-admin-success@example.com",
    )

    db_session.flush()
    assert user.role == UserRole.admin
    event = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.user_id == user.id,
            AuditLog.event_type == "first_admin_bootstrap",
        )
        .one()
    )
    assert "server-side bootstrap" in event.description


def test_bootstrap_preserves_email_local_part_case(db_session):
    email = "Owner.Case@example.com"
    user = _add_user(db_session, email)

    promote_initial_admin(db_session, email, email)

    assert user.role == UserRole.admin

def test_bootstrap_rejects_unverified_account(db_session):
    user = _add_user(db_session, "first-admin-unverified@example.com", verified=False)

    with pytest.raises(ValueError, match="تأكيد البريد"):
        promote_initial_admin(
            db_session,
            "first-admin-unverified@example.com",
            "first-admin-unverified@example.com",
        )

    assert user.role == UserRole.user


def test_bootstrap_rejects_inactive_account(db_session):
    user = _add_user(db_session, "first-admin-inactive@example.com", active=False)

    with pytest.raises(ValueError, match="معطّل"):
        promote_initial_admin(
            db_session,
            "first-admin-inactive@example.com",
            "first-admin-inactive@example.com",
        )

    assert user.role == UserRole.user


def test_bootstrap_rejects_when_an_admin_already_exists(db_session):
    _add_user(db_session, "existing-admin@example.com", role=UserRole.admin)
    target = _add_user(db_session, "second-admin@example.com")

    with pytest.raises(ValueError, match="يوجد مدير"):
        promote_initial_admin(
            db_session,
            "second-admin@example.com",
            "second-admin@example.com",
        )

    assert target.role == UserRole.user


def test_bootstrap_requires_exact_email_confirmation(db_session):
    user = _add_user(db_session, "first-admin-confirm@example.com")

    with pytest.raises(ValueError, match="لم يتطابق"):
        promote_initial_admin(
            db_session,
            "first-admin-confirm@example.com",
            "someone-else@example.com",
        )

    assert user.role == UserRole.user


def test_bootstrap_rejects_missing_account(db_session):
    with pytest.raises(ValueError, match="الحساب غير موجود"):
        promote_initial_admin(
            db_session,
            "not-registered@example.com",
            "not-registered@example.com",
        )


def test_concurrent_bootstrap_serializes_and_creates_exactly_one_admin(db_session):
    """Two independent sessions cannot both pass the no-admin check."""
    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    ConcurrentSession = sessionmaker(bind=engine, expire_on_commit=False)
    suffix = uuid4().hex
    email_a = f"bootstrap-a-{suffix}@example.com"
    email_b = f"bootstrap-b-{suffix}@example.com"

    with ConcurrentSession.begin() as setup:
        _add_user(setup, email_a)
        _add_user(setup, email_b)

    first_promoted = Event()
    release_first = Event()
    second_observed_lock = Event()

    def run_first():
        with ConcurrentSession() as session:
            with session.begin():
                promote_initial_admin(session, email_a, email_a)
                first_promoted.set()
                if not release_first.wait(timeout=10):
                    raise AssertionError("Timed out waiting to release the first bootstrap transaction.")
        return "promoted"

    def run_second():
        if not first_promoted.wait(timeout=10):
            raise AssertionError("The first bootstrap did not acquire the lock.")

        # Confirm that a second transaction cannot acquire the same advisory lock
        # while the first transaction is still open.
        with ConcurrentSession() as probe:
            with probe.begin():
                acquired = probe.execute(
                    text("SELECT pg_try_advisory_xact_lock(:namespace, :lock_id)"),
                    {
                        "namespace": _ADMIN_BOOTSTRAP_LOCK_NAMESPACE,
                        "lock_id": _ADMIN_BOOTSTRAP_LOCK_ID,
                    },
                ).scalar_one()
                assert acquired is False
                second_observed_lock.set()

        try:
            with ConcurrentSession() as session:
                with session.begin():
                    promote_initial_admin(session, email_b, email_b)
        except ValueError as exc:
            return str(exc)
        return "unexpected second promotion"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first_future = pool.submit(run_first)
            assert first_promoted.wait(timeout=10)
            second_future = pool.submit(run_second)
            assert second_observed_lock.wait(timeout=10)
            release_first.set()
            assert first_future.result(timeout=10) == "promoted"
            assert "يوجد مدير" in second_future.result(timeout=10)

        with ConcurrentSession() as verify:
            admins = (
                verify.query(User)
                .filter(User.email.in_([email_a, email_b]), User.role == UserRole.admin)
                .count()
            )
            assert admins == 1
    finally:
        release_first.set()
        with ConcurrentSession.begin() as cleanup:
            user_ids = (
                cleanup.query(User.id)
                .filter(User.email.in_([email_a, email_b]))
                .subquery()
            )
            cleanup.query(AuditLog).filter(AuditLog.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            cleanup.query(User).filter(User.email.in_([email_a, email_b])).delete(
                synchronize_session=False
            )


def test_confirmation_phrase_identifies_target_without_credentials():
    from sqlalchemy.engine import URL

    from app.ops.promote_initial_admin import _build_confirmation_phrase

    url = URL.create(
        drivername="postgresql+psycopg2",
        username="private-user",
        password="private-password",
        host="db.example.internal",
        port=5432,
        database="lumen_prod",
        query={"sslmode": "require"},
    )
    phrase = _build_confirmation_phrase(
        "owner@example.com", "production", url
    )

    assert phrase == "owner@example.com | production | db.example.internal:5432/lumen_prod"
    assert "private-user" not in phrase
    assert "private-password" not in phrase
    assert "sslmode" not in phrase
