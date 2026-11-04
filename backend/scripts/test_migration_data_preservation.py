"""Exercise populated legacy-data preservation and verify schema downgrade.

This script requires a dedicated, disposable PostgreSQL database. It refuses to
use any database except the explicitly named CI database below.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_DATABASE_NAME = "lumen_migration_preservation_test"


def run_alembic(database_url: str, *args: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env.setdefault("ENVIRONMENT", "development")
    env.setdefault("JWT_SECRET_KEY", "ci-only-migration-test-secret-not-for-deployment")
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
    )


def create_dedicated_database(database_url: str) -> None:
    url = make_url(database_url)
    if url.database != EXPECTED_DATABASE_NAME:
        raise RuntimeError(
            f"Refusing to run against {url.database!r}; expected {EXPECTED_DATABASE_NAME!r}"
        )

    admin_url = url.set(database="postgres").render_as_string(hide_password=False)
    connection = psycopg2.connect(admin_url)
    try:
        # CREATE DATABASE is forbidden inside a transaction block.
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (EXPECTED_DATABASE_NAME,),
            )
            if cursor.fetchone():
                raise RuntimeError(
                    f"Database {EXPECTED_DATABASE_NAME!r} already exists. "
                    "Use a fresh disposable CI database; this script never drops databases."
                )
            cursor.execute(f'CREATE DATABASE "{EXPECTED_DATABASE_NAME}"')
    finally:
        connection.close()


def create_test_engine(database_url: str):
    # Match the explicit driver selected by the application and requirements.txt.
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg2")
    return create_engine(url)


def seed_legacy_rows(database_url: str) -> tuple[int, int, int, int]:
    engine = create_test_engine(database_url)
    with engine.begin() as connection:
        user_id = connection.execute(
            text(
                """
                INSERT INTO users (
                    email, hashed_password, role, is_active, totp_secret, is_2fa_enabled
                )
                VALUES (
                    :email, :password_hash, 'user', TRUE, 'JBSWY3DPEHPK3PXP', TRUE
                )
                RETURNING id
                """
            ),
            {
                "email": "migration-preservation@example.test",
                "password_hash": "not-a-real-password-hash",
            },
        ).scalar_one()

        conversation_id = connection.execute(
            text(
                """
                INSERT INTO conversations (user_id, title)
                VALUES (:user_id, :title)
                RETURNING id
                """
            ),
            {"user_id": user_id, "title": "Legacy conversation to preserve"},
        ).scalar_one()

        message_id = connection.execute(
            text(
                """
                INSERT INTO messages (conversation_id, role, content)
                VALUES (:conversation_id, 'user', :content)
                RETURNING id
                """
            ),
            {
                "conversation_id": conversation_id,
                "content": "Legacy message must survive the education migration.",
            },
        ).scalar_one()

        usage_id = connection.execute(
            text(
                """
                INSERT INTO usage_logs (user_id, endpoint, input_tokens, output_tokens)
                VALUES (:user_id, '/chat/completions', 123, 456)
                RETURNING id
                """
            ),
            {"user_id": user_id},
        ).scalar_one()

        connection.execute(
            text("SELECT id FROM plans WHERE name = 'Pro' ORDER BY id LIMIT 1")
        ).scalar_one()

        assignment_id = connection.execute(
            text(
                """
                INSERT INTO assignments (created_by_user_id, title, description)
                VALUES (:user_id, 'Legacy assignment', 'Preserve the old AI assessment')
                RETURNING id
                """
            ),
            {"user_id": user_id},
        ).scalar_one()

        submission_id = connection.execute(
            text(
                """
                INSERT INTO assignment_submissions (
                    assignment_id, student_user_id, written_answer,
                    simulation_achieved_value, simulation_passed,
                    ai_grade_percentage, ai_feedback, status,
                    submitted_at, graded_at
                )
                VALUES (
                    :assignment_id, :user_id, 'Student answer',
                    7.5, TRUE, 91.25, 'Legacy AI feedback', 'graded',
                    now(), now()
                )
                RETURNING id
                """
            ),
            {"assignment_id": assignment_id, "user_id": user_id},
        ).scalar_one()

    engine.dispose()
    return user_id, message_id, usage_id, submission_id


def verify_archived_state(database_url: str, ids: tuple[int, int, int, int]) -> None:
    user_id, message_id, usage_id, submission_id = ids
    engine = create_test_engine(database_url)
    with engine.connect() as connection:
        message = connection.execute(
            text(
                """
                SELECT m.content, c.title, c.user_id
                FROM legacy_ai_messages AS m
                JOIN legacy_ai_conversations AS c ON c.id = m.conversation_id
                WHERE m.id = :message_id
                """
            ),
            {"message_id": message_id},
        ).mappings().one()
        assert message["content"] == "Legacy message must survive the education migration."
        assert message["title"] == "Legacy conversation to preserve"
        assert message["user_id"] == user_id

        legacy_totp = connection.execute(
            text("SELECT totp_secret, is_2fa_enabled FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        ).one()
        assert legacy_totp == ("JBSWY3DPEHPK3PXP", True)
        webhook_table = connection.execute(
            text("SELECT to_regclass('public.processed_webhook_events')")
        ).scalar_one()
        assert webhook_table is not None
        auth_sessions_table = connection.execute(
            text("SELECT to_regclass('public.auth_sessions')")
        ).scalar_one()
        assert auth_sessions_table is not None
        totp_column_length = connection.execute(
            text(
                """
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'totp_secret'
                """
            )
        ).scalar_one()
        assert totp_column_length == 255

        usage = connection.execute(
            text(
                """
                SELECT endpoint, input_tokens, output_tokens
                FROM legacy_ai_usage_logs
                WHERE id = :usage_id AND user_id = :user_id
                """
            ),
            {"usage_id": usage_id, "user_id": user_id},
        ).mappings().one()
        assert usage == {
            "endpoint": "/chat/completions",
            "input_tokens": 123,
            "output_tokens": 456,
        }

        plan_limit = connection.execute(
            text(
                """
                SELECT legacy_daily_ai_request_limit
                FROM plans WHERE name = 'Pro'
                ORDER BY id LIMIT 1
                """
            )
        ).scalar_one()
        assert plan_limit == 500

        submission = connection.execute(
            text(
                """
                SELECT legacy_ai_grade_percentage, legacy_ai_feedback,
                       legacy_ai_simulation_achieved_value, legacy_ai_simulation_passed,
                       legacy_ai_status, legacy_ai_graded_at,
                       grade_percentage, feedback, status, graded_at
                FROM assignment_submissions WHERE id = :submission_id
                """
            ),
            {"submission_id": submission_id},
        ).mappings().one()
        assert submission["legacy_ai_grade_percentage"] == 91.25
        assert submission["legacy_ai_feedback"] == "Legacy AI feedback"
        assert submission["legacy_ai_simulation_achieved_value"] == 7.5
        assert submission["legacy_ai_simulation_passed"] is True
        assert submission["legacy_ai_status"] == "graded"
        assert submission["legacy_ai_graded_at"] is not None
        assert submission["grade_percentage"] is None
        assert submission["feedback"] is None
        assert submission["status"] == "submitted"
        assert submission["graded_at"] is None

    engine.dispose()


def verify_downgraded_state(database_url: str, ids: tuple[int, int, int, int]) -> None:
    user_id, message_id, usage_id, submission_id = ids
    engine = create_test_engine(database_url)
    with engine.connect() as connection:
        message = connection.execute(
            text(
                """
                SELECT m.content, c.title, c.user_id
                FROM messages AS m
                JOIN conversations AS c ON c.id = m.conversation_id
                WHERE m.id = :message_id
                """
            ),
            {"message_id": message_id},
        ).mappings().one()
        assert message["content"] == "Legacy message must survive the education migration."
        assert message["title"] == "Legacy conversation to preserve"
        assert message["user_id"] == user_id

        legacy_totp = connection.execute(
            text("SELECT totp_secret, is_2fa_enabled FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        ).one()
        assert legacy_totp == ("JBSWY3DPEHPK3PXP", True)
        webhook_table = connection.execute(
            text("SELECT to_regclass('public.processed_webhook_events')")
        ).scalar_one()
        assert webhook_table is None
        auth_sessions_table = connection.execute(
            text("SELECT to_regclass('public.auth_sessions')")
        ).scalar_one()
        assert auth_sessions_table is None
        totp_column_length = connection.execute(
            text(
                """
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'totp_secret'
                """
            )
        ).scalar_one()
        # Downgrade deliberately keeps VARCHAR(255) to avoid truncating ciphertext.
        assert totp_column_length == 255

        usage = connection.execute(
            text(
                """
                SELECT endpoint, input_tokens, output_tokens
                FROM usage_logs
                WHERE id = :usage_id AND user_id = :user_id
                """
            ),
            {"usage_id": usage_id, "user_id": user_id},
        ).mappings().one()
        assert usage["endpoint"] == "/chat/completions"
        assert usage["input_tokens"] == 123
        assert usage["output_tokens"] == 456

        plan_limit = connection.execute(
            text(
                "SELECT daily_ai_request_limit FROM plans WHERE name = 'Pro' ORDER BY id LIMIT 1"
            )
        ).scalar_one()
        assert plan_limit == 500

        submission = connection.execute(
            text(
                """
                SELECT ai_grade_percentage, ai_feedback, simulation_achieved_value,
                       simulation_passed, status, graded_at
                FROM assignment_submissions WHERE id = :submission_id
                """
            ),
            {"submission_id": submission_id},
        ).mappings().one()
        assert submission["ai_grade_percentage"] == 91.25
        assert submission["ai_feedback"] == "Legacy AI feedback"
        assert submission["simulation_achieved_value"] == 7.5
        assert submission["simulation_passed"] is True
        assert submission["status"] == "graded"
        assert submission["graded_at"] is not None

        archived_tables = connection.execute(
            text(
                """
                SELECT to_regclass('public.legacy_ai_messages'),
                       to_regclass('public.legacy_ai_conversations'),
                       to_regclass('public.legacy_ai_usage_logs')
                """
            )
        ).one()
        assert archived_tables == (None, None, None)

    engine.dispose()


def main() -> None:
    raw_url = os.environ.get("MIGRATION_TEST_DATABASE_URL")
    if not raw_url:
        raise RuntimeError("MIGRATION_TEST_DATABASE_URL is required")

    database_url = make_url(raw_url).render_as_string(hide_password=False)
    create_dedicated_database(database_url)
    run_alembic(database_url, "upgrade", "0014_lti")
    ids = seed_legacy_rows(database_url)

    run_alembic(database_url, "upgrade", "head")
    verify_archived_state(database_url, ids)

    run_alembic(database_url, "downgrade", "0014_lti")
    verify_downgraded_state(database_url, ids)
    print(
        "Database migration regression passed: legacy AI data, assessment data, TOTP "
        "secrets, webhook idempotency, and auth-session schema behaved correctly across upgrade/downgrade."
    )


if __name__ == "__main__":
    main()
