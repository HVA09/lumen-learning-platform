"""Tests for provider-neutral, encrypted Restic offsite backup orchestration."""

import gzip
import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "offsite-backup.sh"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _environment(
    tmp_path: Path,
    *,
    snapshots: str = "[]",
    snapshot_exists: str = "0",
    fail_command: str = "",
) -> tuple[dict[str, str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    calls_file = tmp_path / "restic-calls.log"
    snapshots_file = tmp_path / "snapshots.json"
    snapshots_file.write_text(snapshots, encoding="utf-8")
    password_file = tmp_path / "restic-password"
    password_file.write_text("ci-only-restic-password\n", encoding="utf-8")

    _write_executable(
        bin_dir / "restic",
        """#!/bin/sh
printf '%s\\n' "$*" >> "$RESTIC_CALL_LOG"
if [ "$1" = "snapshots" ]; then
  cat "$RESTIC_SNAPSHOT_JSON"
fi
if [ -n "${RESTIC_FAIL_COMMAND:-}" ] && [ "$1" = "$RESTIC_FAIL_COMMAND" ]; then
  exit 47
fi
exit 0
""",
    )
    _write_executable(
        bin_dir / "jq",
        """#!/bin/sh
if [ "$1" = "-e" ]; then
  shift
fi
source_path=""
if [ "$1" = "--arg" ]; then
  shift
  variable_name="$1"
  source_path="$2"
  shift 2
fi
expression="$1"
input=$(cat)
case "$expression" in
  'type == "array"')
    printf '%s\\n' "$input" | grep -q '^\\['
    ;;
  *)
    [ -n "$source_path" ] || exit 1
    printf '%s\\n' "$input" | grep -F -q "\\\"$source_path\\\""
    ;;
esac
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env.get('PATH', '')}",
            "RESTIC_REPOSITORY": "s3:https://storage.example.test/lumen",
            "RESTIC_PASSWORD_FILE": str(password_file),
            "RESTIC_BACKUP_TAG": "lumen-postgres",
            "RESTIC_KEEP_DAILY": "7",
            "RESTIC_KEEP_WEEKLY": "4",
            "RESTIC_KEEP_MONTHLY": "12",
            "RESTIC_KEEP_YEARLY": "3",
            "BACKUP_DIR": str(tmp_path / "backups"),
            "RESTIC_CALL_LOG": str(calls_file),
            "RESTIC_SNAPSHOT_JSON": str(snapshots_file),
            "RESTIC_FAIL_COMMAND": fail_command,
        }
    )
    return env, calls_file


def _archive(directory: Path, name: str, contents: bytes = b"test database dump") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    with gzip.open(path, "wb") as output:
        output.write(contents)
    return path


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _calls(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def test_offsite_backup_uploads_only_latest_archive_and_applies_retention(
    tmp_path: Path,
) -> None:
    env, calls_file = _environment(tmp_path)
    backup_dir = Path(env["BACKUP_DIR"])
    _archive(backup_dir, "backup_20261029_010000.sql.gz")
    latest = _archive(backup_dir, "backup_20261031_010000.sql.gz")

    result = _run(env)

    assert result.returncode == 0, result.stderr
    calls = _calls(calls_file)
    oldest = backup_dir / "backup_20261029_010000.sql.gz"
    assert calls[0] == "cat config"
    assert calls[1] == "snapshots --json --tag lumen-postgres"
    assert calls[2] == f"backup --tag lumen-postgres --group-by host,tags {oldest}"
    assert calls[3] == f"backup --tag lumen-postgres --group-by host,tags {latest}"
    assert calls[4] == (
        "forget --group-by host,tags --tag lumen-postgres "
        "--keep-daily 7 --keep-weekly 4 --keep-monthly 12 "
        "--keep-yearly 3 --prune"
    )
    assert calls[5] == "check"
    assert len(calls) == 6
    assert latest.exists(), "Offsite upload must not delete local recovery copies."


def test_offsite_backup_skips_archive_already_present_in_repository(
    tmp_path: Path,
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    latest = _archive(backup_dir, "backup_20261031_010000.sql.gz")
    snapshots = (
        '[{"id":"snapshot-id","paths":['
        f'"{latest}"'
        '],"tags":["lumen-postgres"]}]'
    )
    env, calls_file = _environment(tmp_path, snapshots=snapshots)

    result = _run(env)

    assert result.returncode == 0, result.stderr
    assert _calls(calls_file) == [
        "cat config",
        "snapshots --json --tag lumen-postgres",
    ]
    assert "already present" in result.stdout


def test_offsite_backup_uploads_only_archives_missing_from_remote_repository(
    tmp_path: Path,
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    already_uploaded = _archive(backup_dir, "backup_20261029_010000.sql.gz")
    pending = _archive(backup_dir, "backup_20261031_010000.sql.gz")
    snapshots = (
        '[{"id":"snapshot-id","paths":['
        f'"{already_uploaded}"'
        '],"tags":["lumen-postgres"]}]'
    )
    env, calls_file = _environment(tmp_path, snapshots=snapshots)

    result = _run(env)

    assert result.returncode == 0, result.stderr
    calls = _calls(calls_file)
    assert calls[2] == f"backup --tag lumen-postgres --group-by host,tags {pending}"
    assert not any(str(already_uploaded) in call for call in calls)
    assert calls[-2].startswith("forget ")
    assert calls[-1] == "check"


def test_offsite_backup_does_not_prune_when_upload_fails(tmp_path: Path) -> None:
    env, calls_file = _environment(tmp_path, fail_command="backup")
    backup_dir = Path(env["BACKUP_DIR"])
    _archive(backup_dir, "backup_20261031_010000.sql.gz")

    result = _run(env)

    assert result.returncode == 47
    calls = _calls(calls_file)
    assert any(call.startswith("backup ") for call in calls)
    assert not any(call.startswith("forget ") for call in calls)
    assert "check" not in calls


def test_offsite_backup_rejects_missing_repository_or_password_file(
    tmp_path: Path,
) -> None:
    env, calls_file = _environment(tmp_path)
    _archive(Path(env["BACKUP_DIR"]), "backup_20261031_010000.sql.gz")

    missing_repository = env.copy()
    missing_repository["RESTIC_REPOSITORY"] = ""
    result = _run(missing_repository)
    assert result.returncode != 0
    assert "RESTIC_REPOSITORY is required" in result.stderr

    missing_password = env.copy()
    missing_password["RESTIC_PASSWORD_FILE"] = str(tmp_path / "missing-password")
    result = _run(missing_password)
    assert result.returncode != 0
    assert "password file is missing or empty" in result.stderr
    assert _calls(calls_file) == []


def test_offsite_backup_waits_without_local_archive(tmp_path: Path) -> None:
    env, calls_file = _environment(tmp_path)
    Path(env["BACKUP_DIR"]).mkdir()

    result = _run(env)

    assert result.returncode == 0
    assert "No local PostgreSQL backup archive" in result.stdout
    assert _calls(calls_file) == []


def test_offsite_backup_rejects_corrupt_local_archive(tmp_path: Path) -> None:
    env, calls_file = _environment(tmp_path)
    backup_dir = Path(env["BACKUP_DIR"])
    backup_dir.mkdir()
    (backup_dir / "backup_20261031_010000.sql.gz").write_bytes(b"not gzip")

    result = _run(env)

    assert result.returncode != 0
    assert _calls(calls_file) == []
