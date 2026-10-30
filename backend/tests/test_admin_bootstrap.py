"""اختبارات أمر تهيئة أول مدير — تعمل على قاعدة PostgreSQL الاختبارية."""
import pytest

from app.models.user import User, UserRole
from scripts.promote_initial_admin import promote_initial_admin


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


def test_bootstrap_promotes_verified_existing_account(db_session):
    user = _add_user(db_session, "owner@example.com", verified=True)

    with db_session.begin_nested():
        promote_initial_admin(db_session, "owner@example.com", "owner@example.com")

    db_session.refresh(user)
    assert user.role == UserRole.admin


def test_bootstrap_rejects_unverified_account(db_session):
    user = _add_user(db_session, "unverified@example.com", verified=False)

    with pytest.raises(ValueError, match="تأكيد البريد"):
        with db_session.begin_nested():
            promote_initial_admin(db_session, "unverified@example.com", "unverified@example.com")

    db_session.refresh(user)
    assert user.role == UserRole.user


def test_bootstrap_rejects_when_an_admin_already_exists(db_session):
    _add_user(db_session, "existing-admin@example.com", role=UserRole.admin)
    target = _add_user(db_session, "new-owner@example.com")

    with pytest.raises(ValueError, match="يوجد مدير"):
        with db_session.begin_nested():
            promote_initial_admin(db_session, "new-owner@example.com", "new-owner@example.com")

    db_session.refresh(target)
    assert target.role == UserRole.user


def test_bootstrap_requires_exact_email_confirmation(db_session):
    user = _add_user(db_session, "owner-confirm@example.com")

    with pytest.raises(ValueError, match="لم يتطابق"):
        promote_initial_admin(db_session, "owner-confirm@example.com", "different@example.com")

    db_session.refresh(user)
    assert user.role == UserRole.user


def test_bootstrap_rejects_inactive_account(db_session):
    user = _add_user(db_session, "disabled@example.com", active=False)

    with pytest.raises(ValueError, match="معطّل"):
        with db_session.begin_nested():
            promote_initial_admin(db_session, "disabled@example.com", "disabled@example.com")

    db_session.refresh(user)
    assert user.role == UserRole.user
