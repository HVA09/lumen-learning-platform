"""Tests for secure first-admin provisioning (PostgreSQL advisory lock)."""
import pytest

from app.bootstrap_admin import promote_verified_account
from app.models.user import User, UserRole


def _add_user(
    db_session,
    email,
    *,
    verified=True,
    active=True,
    role=UserRole.user,
):
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


def test_bootstrap_promotes_existing_verified_account(db_session):
    user = _add_user(db_session, "owner@example.com")

    promoted = promote_verified_account(db_session, "OWNER@example.com")

    assert promoted.id == user.id
    assert promoted.role == UserRole.admin


def test_bootstrap_rejects_unverified_account(db_session):
    user = _add_user(db_session, "unverified@example.com", verified=False)

    with pytest.raises(ValueError, match="Verify the account email"):
        promote_verified_account(db_session, "unverified@example.com")

    db_session.refresh(user)
    assert user.role == UserRole.user


def test_bootstrap_rejects_inactive_account(db_session):
    user = _add_user(db_session, "disabled@example.com", active=False)

    with pytest.raises(ValueError, match="Inactive accounts"):
        promote_verified_account(db_session, "disabled@example.com")

    db_session.refresh(user)
    assert user.role == UserRole.user


def test_bootstrap_refuses_a_second_admin(db_session):
    _add_user(db_session, "existing-admin@example.com", role=UserRole.admin)
    target = _add_user(db_session, "another-admin@example.com")

    with pytest.raises(ValueError, match="administrator already exists"):
        promote_verified_account(db_session, "another-admin@example.com")

    db_session.refresh(target)
    assert target.role == UserRole.user


def test_bootstrap_requires_existing_account(db_session):
    with pytest.raises(ValueError, match="Account not found"):
        promote_verified_account(db_session, "missing@example.com")
