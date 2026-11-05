from types import SimpleNamespace

import pytest

from app import database, tasks
from app.models.user import User
from app.services import reports


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.was_distinct = False

    def filter(self, *conditions):
        self.filters.extend(conditions)
        return self

    def distinct(self):
        self.was_distinct = True
        return self

    def all(self):
        return self.rows


class FakeDatabase:
    def __init__(self, query_rows=(), users=None):
        self.query_result = FakeQuery(list(query_rows))
        self.users = users or {}
        self.closed = False
        self.queried_entities = []

    def query(self, entity):
        self.queried_entities.append(entity)
        return self.query_result

    def get(self, model, user_id):
        assert model is User
        return self.users.get(user_id)

    def close(self):
        self.closed = True


def test_queue_email_uses_celery_when_available(monkeypatch):
    queued = []
    sent_directly = []

    monkeypatch.setattr(tasks, "_CELERY_AVAILABLE", True)
    monkeypatch.setattr(
        tasks,
        "send_email_task",
        SimpleNamespace(delay=lambda *args: queued.append(args)),
    )
    monkeypatch.setattr(
        tasks, "send_email", lambda *args: sent_directly.append(args)
    )

    tasks.queue_email("student@example.test", "Subject", "Body")

    assert queued == [("student@example.test", "Subject", "Body")]
    assert sent_directly == []


def test_queue_email_falls_back_to_direct_send_when_celery_is_unavailable(monkeypatch):
    sent = []
    monkeypatch.setattr(tasks, "_CELERY_AVAILABLE", False)
    monkeypatch.setattr(
        tasks, "send_email", lambda *args: sent.append(args)
    )

    tasks.queue_email("student@example.test", "Subject", "Body")

    assert sent == [("student@example.test", "Subject", "Body")]


def test_queue_email_falls_back_when_redis_enqueue_fails(monkeypatch):
    sent = []

    def fail_to_enqueue(*_args):
        raise ConnectionError("Redis unavailable")

    monkeypatch.setattr(tasks, "_CELERY_AVAILABLE", True)
    monkeypatch.setattr(
        tasks, "send_email_task", SimpleNamespace(delay=fail_to_enqueue)
    )
    monkeypatch.setattr(
        tasks, "send_email", lambda *args: sent.append(args)
    )

    tasks.queue_email("student@example.test", "Subject", "Body")

    assert sent == [("student@example.test", "Subject", "Body")]


def test_send_email_task_delegates_to_email_service(monkeypatch):
    sent = []
    monkeypatch.setattr(
        tasks, "send_email", lambda *args: sent.append(args)
    )

    tasks.send_email_task.run(
        "student@example.test", "Subject", "Body"
    )

    assert sent == [("student@example.test", "Subject", "Body")]


def test_weekly_digest_sends_only_for_users_with_activity(monkeypatch):
    active_user = SimpleNamespace(id=10, email="active@example.test")
    new_user = SimpleNamespace(id=11, email="new@example.test")
    db = FakeDatabase(query_rows=[active_user, new_user])
    sent = []
    reports_seen = {
        10: {"topics_practiced": 3},
        11: {"topics_practiced": 0},
    }

    monkeypatch.setattr(database, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        reports,
        "build_progress_report",
        lambda _db, user_id: reports_seen[user_id],
    )
    monkeypatch.setattr(
        reports,
        "format_report_email_body",
        lambda report: f"topics={report['topics_practiced']}",
    )
    monkeypatch.setattr(
        tasks, "send_email", lambda *args: sent.append(args)
    )

    tasks.send_weekly_digests_task.run()

    assert sent == [
        ("active@example.test", "ملخص تقدّمك الأسبوعي", "topics=3")
    ]
    assert db.closed is True


def test_weekly_digest_closes_database_when_report_generation_fails(monkeypatch):
    db = FakeDatabase(query_rows=[SimpleNamespace(id=10, email="active@example.test")])
    monkeypatch.setattr(database, "SessionLocal", lambda: db)

    def fail_to_build_report(_db, _user_id):
        raise RuntimeError("Report generation failed")

    monkeypatch.setattr(reports, "build_progress_report", fail_to_build_report)

    with pytest.raises(RuntimeError, match="Report generation failed"):
        tasks.send_weekly_digests_task.run()

    assert db.closed is True


def test_due_card_reminder_notifies_only_existing_active_users(monkeypatch):
    active_user = SimpleNamespace(id=1, is_active=True)
    inactive_user = SimpleNamespace(id=2, is_active=False)
    db = FakeDatabase(
        query_rows=[(1,), (2,), (3,)],
        users={1: active_user, 2: inactive_user},
    )
    notified = []

    monkeypatch.setattr(database, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        tasks,
        "notify",
        lambda *args: notified.append(args),
        raising=False,
    )

    tasks.send_due_cards_reminders_task.run()

    assert len(notified) == 1
    assert notified[0][0] is db
    assert notified[0][1:] == (
        1,
        "بطاقات مراجعة بانتظارك",
        "عندك بطاقات تكرار متباعد مستحقة اليوم — راجعها قبل ما تنسى المحتوى",
        "reminder",
    )
    assert db.closed is True
    assert db.query_result.was_distinct is True
