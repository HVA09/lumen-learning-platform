"""Regression tests for safe PostgreSQL backup and restore shell scripts."""

import os
import subprocess
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
BACKUP_SCRIPT = SCRIPTS_DIR / "backup.sh"
RESTORE_SCRIPT = SCRIPTS_DIR / "restore.sh"


def _write_executable(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


def _script_env(tmp_path: Path, backup_dir: Path, bin_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["BACKUP_DIR"] = str(backup_dir)
    env["DATABASE_URL"] = "postgresql://test:test@localhost/test"
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    return env


def test_backup_does_not_publish_archive_when_pg_dump_fails(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "pg_dump",
        "#!/bin/sh\necho 'simulated pg_dump failure' >&2\nexit 23\n",
    )

    result = subprocess.run(
        ["sh", str(BACKUP_SCRIPT)],
        env=_script_env(tmp_path, backup_dir, bin_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 23
    assert list(backup_dir.glob("backup_*.sql.gz")) == []
    assert list(backup_dir.iterdir()) == []


def test_backup_publishes_only_a_complete_valid_gzip_archive(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "pg_dump",
        "#!/bin/sh\nprintf '%s\\n' '-- PostgreSQL test dump' 'SELECT 1;'\n",
    )

    result = subprocess.run(
        ["sh", str(BACKUP_SCRIPT)],
        env=_script_env(tmp_path, backup_dir, bin_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    archives = list(backup_dir.glob("backup_*.sql.gz"))
    assert len(archives) == 1
    assert archives[0].stat().st_size > 0

    gzip_check = subprocess.run(
        ["gzip", "-t", str(archives[0])],
        capture_output=True,
        text=True,
        check=False,
    )
    assert gzip_check.returncode == 0, gzip_check.stderr
    assert sorted(path.name for path in backup_dir.iterdir()) == [archives[0].name]



def test_backup_does_not_publish_or_prune_when_compression_fails(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    bin_dir = tmp_path / "bin"
    backup_dir.mkdir()
    bin_dir.mkdir()
    old_archive = backup_dir / "backup_previous.sql.gz"
    old_archive.write_bytes(b"previous verified backup")
    old_time = old_archive.stat().st_mtime - (10 * 24 * 60 * 60)
    os.utime(old_archive, (old_time, old_time))

    _write_executable(
        bin_dir / "pg_dump",
        "#!/bin/sh\nprintf '%s\\n' '-- PostgreSQL test dump' 'SELECT 1;'\n",
    )
    _write_executable(
        bin_dir / "gzip",
        "#!/bin/sh\necho 'simulated compression failure' >&2\nexit 45\n",
    )

    result = subprocess.run(
        ["sh", str(BACKUP_SCRIPT)],
        env=_script_env(tmp_path, backup_dir, bin_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 45
    assert old_archive.read_bytes() == b"previous verified backup"
    assert sorted(path.name for path in backup_dir.iterdir()) == [old_archive.name]
    assert list(backup_dir.glob("backup_*.sql.gz.tmp.*")) == []

def test_restore_rejects_corrupt_archive_before_running_psql(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    bin_dir = tmp_path / "bin"
    backup_dir.mkdir()
    bin_dir.mkdir()
    corrupt_archive = backup_dir / "backup_corrupt.sql.gz"
    corrupt_archive.write_bytes(b"not a gzip archive")
    psql_marker = tmp_path / "psql-was-called"
    _write_executable(
        bin_dir / "psql",
        f"#!/bin/sh\nprintf called > '{psql_marker}'\n",
    )

    result = subprocess.run(
        ["sh", str(RESTORE_SCRIPT), str(corrupt_archive), "--confirm"],
        env=_script_env(tmp_path, backup_dir, bin_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert not psql_marker.exists()



def test_restore_does_not_call_psql_when_decompression_fails(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    bin_dir = tmp_path / "bin"
    backup_dir.mkdir()
    bin_dir.mkdir()
    archive = backup_dir / "backup_decompression_failure.sql.gz"
    archive.write_bytes(b"stubbed archive")
    psql_marker = tmp_path / "psql-was-called"

    _write_executable(
        bin_dir / "gzip",
        "#!/bin/sh\n# Simulate the prior archive validation succeeding.\nexit 0\n",
    )
    _write_executable(
        bin_dir / "gunzip",
        "#!/bin/sh\nprintf '%s\\n' 'SELECT 1;'\nexit 46\n",
    )
    _write_executable(
        bin_dir / "psql",
        f"#!/bin/sh\nprintf called > '{psql_marker}'\n",
    )

    result = subprocess.run(
        ["sh", str(RESTORE_SCRIPT), str(archive), "--confirm"],
        env=_script_env(tmp_path, backup_dir, bin_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 46
    assert not psql_marker.exists()
    assert sorted(path.name for path in backup_dir.iterdir()) == [archive.name]

def test_restore_requires_explicit_confirmation(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    bin_dir = tmp_path / "bin"
    backup_dir.mkdir()
    bin_dir.mkdir()
    archive = backup_dir / "backup_valid.sql.gz"
    archive.write_bytes(b"not needed without confirmation")
    psql_marker = tmp_path / "psql-was-called"
    _write_executable(
        bin_dir / "psql",
        f"#!/bin/sh\nprintf called > '{psql_marker}'\n",
    )

    result = subprocess.run(
        ["sh", str(RESTORE_SCRIPT), str(archive)],
        env=_script_env(tmp_path, backup_dir, bin_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert not psql_marker.exists()
