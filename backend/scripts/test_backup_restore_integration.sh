#!/bin/sh
# End-to-end backup/restore smoke test against a disposable CI PostgreSQL service.
# This script is intentionally restricted to GitHub Actions and localhost PostgreSQL.
set -eu

if [ "${GITHUB_ACTIONS:-}" != "true" ]; then
  echo "This destructive smoke test may only run inside GitHub Actions." >&2
  exit 2
fi

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
: "${PGPASSWORD:?PGPASSWORD must be set to the disposable CI PostgreSQL password}"
export PGHOST PGPORT PGUSER PGPASSWORD

case "$PGHOST" in
  localhost|127.0.0.1) ;;
  *)
    echo "Refusing to run: PGHOST must point to localhost." >&2
    exit 2
    ;;
esac

for command_name in createdb dropdb pg_dump psql gzip gunzip mktemp stat; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required PostgreSQL/utility command not found: $command_name" >&2
    exit 2
  fi
done

TEST_DATABASE_NAME="lumen_backup_restore_${GITHUB_RUN_ID:-0}_${GITHUB_RUN_ATTEMPT:-1}"
BACKUP_DIR=$(mktemp -d "${RUNNER_TEMP:-/tmp}/lumen-backup-restore.XXXXXX")
DATABASE_CREATED=0

cleanup() {
  result=$?
  if [ "$DATABASE_CREATED" -eq 1 ]; then
    dropdb --if-exists --maintenance-db=postgres "$TEST_DATABASE_NAME" >/dev/null 2>&1 || true
  fi
  rm -rf "$BACKUP_DIR"
  exit "$result"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

# This database name is reserved for this CI smoke test. Never point this script
# at a production or shared PostgreSQL server.
createdb --maintenance-db=postgres "$TEST_DATABASE_NAME"
DATABASE_CREATED=1

psql --set=ON_ERROR_STOP=1 --dbname="$TEST_DATABASE_NAME" <<'SQL'
CREATE TABLE public.backup_restore_probe (
    id integer PRIMARY KEY,
    payload text NOT NULL
);
INSERT INTO public.backup_restore_probe (id, payload)
VALUES (7, 'before-restore');
SQL

DATABASE_URL="dbname=$TEST_DATABASE_NAME" BACKUP_DIR="$BACKUP_DIR" sh scripts/backup.sh

set -- "$BACKUP_DIR"/backup_*.sql.gz
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo "Expected exactly one completed backup archive." >&2
  exit 1
fi
BACKUP_FILE=$1

ARCHIVE_MODE=$(stat -c '%a' "$BACKUP_FILE")
if [ "$ARCHIVE_MODE" != "600" ]; then
  echo "Backup archive permissions must be 600; got $ARCHIVE_MODE." >&2
  exit 1
fi

# Change the saved row after the backup. Restore must return the original value.
psql --set=ON_ERROR_STOP=1 --dbname="$TEST_DATABASE_NAME" \
  --command="UPDATE public.backup_restore_probe SET payload = 'after-backup' WHERE id = 7"

DATABASE_URL="dbname=$TEST_DATABASE_NAME" BACKUP_DIR="$BACKUP_DIR" \
  sh scripts/restore.sh "$BACKUP_FILE" --confirm

RESTORED_VALUE=$(psql --no-align --tuples-only --quiet \
  --set=ON_ERROR_STOP=1 --dbname="$TEST_DATABASE_NAME" \
  --command="SELECT id || ':' || payload FROM public.backup_restore_probe WHERE id = 7")

if [ "$RESTORED_VALUE" != "7:before-restore" ]; then
  echo "Restore verification failed: expected original row, got '$RESTORED_VALUE'." >&2
  exit 1
fi

echo "PostgreSQL backup/restore integration smoke test passed."
