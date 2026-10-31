"""End-to-end backup/restore drill against a disposable PostgreSQL database.

This script is intentionally CI-only. It refuses to run unless the database
name exactly matches the dedicated backup/restore test database and will not
drop or recreate an existing database.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg2
from sqlalchemy.engine import make_url


BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BACKEND_DIR / "scripts"
EXPECTED_DATABASE_NAME = "lumen_backup_restore_test"


def run_command(command: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


def create_dedicated_database(database_url: str) -> None:
    url = make_url(database_url)
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg2"}:
        raise RuntimeError("The backup/restore drill requires a PostgreSQL URL.")
    if url.database != EXPECTED_DATABASE_NAME:
        raise RuntimeError(
            f"Refusing to use {url.database!r}; expected {EXPECTED_DATABASE_NAME!r}."
        )

    admin_url = url.set(database="postgres").render_as_string(hide_password=False)
    connection = psycopg2.connect(admin_url)
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (EXPECTED_DATABASE_NAME,),
            )
            if cursor.fetchone():
                raise RuntimeError(
                    f"Database {EXPECTED_DATABASE_NAME!r} already exists. "
                    "The drill only runs against a fresh disposable CI database."
                )
            cursor.execute(f'CREATE DATABASE "{EXPECTED_DATABASE_NAME}"')
    finally:
        connection.close()


def verify_client_version(database_url: str, env: dict[str, str]) -> None:
    version_text = run_command(["pg_dump", "--version"], env)
    match = re.search(r"\b(\d+)(?:\.\d+)?\b", version_text)
    if not match:
        raise RuntimeError(f"Could not parse pg_dump version: {version_text.strip()}")

    client_major = int(match.group(1))
    with psycopg2.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('server_version_num')::integer")
            server_major = cursor.fetchone()[0] // 10000

    if client_major != server_major:
        raise RuntimeError(
            f"pg_dump major version {client_major} must match PostgreSQL "
            f"server major version {server_major} for this restore drill."
        )


def main() -> None:
    raw_url = os.environ.get("BACKUP_RESTORE_TEST_DATABASE_URL")
    if not raw_url:
        raise RuntimeError("BACKUP_RESTORE_TEST_DATABASE_URL is required.")

    database_url = make_url(raw_url).render_as_string(hide_password=False)
    create_dedicated_database(database_url)

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    verify_client_version(database_url, env)

    expected_rows = [(1, "before-backup"), (2, "second-original-row")]
    with psycopg2.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE backup_restore_probe (
                    id INTEGER PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            cursor.executemany(
                "INSERT INTO backup_restore_probe (id, value) VALUES (%s, %s)",
                expected_rows,
            )

    with tempfile.TemporaryDirectory(prefix="lumen-backup-restore-") as temp_dir:
        backup_dir = Path(temp_dir) / "backups"
        backup_dir.mkdir()
        env["BACKUP_DIR"] = str(backup_dir)

        run_command(["sh", str(SCRIPTS_DIR / "backup.sh")], env)
        archives = list(backup_dir.glob("backup_*.sql.gz"))
        if len(archives) != 1:
            raise RuntimeError(
                f"Expected exactly one published backup archive; found {len(archives)}."
            )

        archive = archives[0]
        if archive.stat().st_size == 0:
            raise RuntimeError("The generated backup archive is empty.")
        if archive.stat().st_mode & 0o077:
            raise RuntimeError("The generated backup archive is accessible by group/other.")
        if list(backup_dir.glob(".backup_*")):
            raise RuntimeError("Backup generation left temporary files behind.")

        # Simulate data loss and verify the restore script recovers the saved rows.
        with psycopg2.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE backup_restore_probe")
                cursor.execute(
                    "INSERT INTO backup_restore_probe (id, value) VALUES (99, 'after-backup')"
                )

        run_command(
            ["sh", str(SCRIPTS_DIR / "restore.sh"), str(archive), "--confirm"],
            env,
        )

        with psycopg2.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, value FROM backup_restore_probe ORDER BY id"
                )
                restored_rows = cursor.fetchall()

        if restored_rows != expected_rows:
            raise RuntimeError(
                f"Restore result mismatch: expected {expected_rows!r}, "
                f"received {restored_rows!r}."
            )
        if list(backup_dir.glob(".restore.sql.*")):
            raise RuntimeError("Restore left its temporary SQL file behind.")

    print(
        "PostgreSQL backup/restore integration drill passed: "
        "created a real pg_dump archive, simulated data loss, restored it with "
        "the production scripts, and verified the original rows."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Backup/restore integration drill failed: {exc}", file=sys.stderr)
        raise
