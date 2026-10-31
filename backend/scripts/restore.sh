#!/bin/sh
# Restore a full PostgreSQL dump. This is destructive and requires an explicit flag.
# Usage:
#   docker compose exec -T backup sh /scripts/restore.sh /backups/backup_XXXXXXXX_XXXXXX.sql.gz --confirm
set -eu

umask 077
BACKUP_DIR="${BACKUP_DIR:-/backups}"
TEMP_SQL=""

cleanup() {
  if [ -n "$TEMP_SQL" ]; then
    rm -f "$TEMP_SQL"
  fi
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

if [ "$#" -ne 2 ] || [ "$2" != "--confirm" ]; then
  echo "Usage: restore.sh <file-under-${BACKUP_DIR}/backup_*.sql.gz> --confirm" >&2
  echo "WARNING: this replaces database objects from the selected backup." >&2
  exit 2
fi

case "$1" in
  "$BACKUP_DIR"/backup_*.sql.gz) ;;
  *)
    echo "The backup file must be inside $BACKUP_DIR and use the backup_*.sql.gz name." >&2
    exit 2
    ;;
esac

if [ ! -f "$1" ]; then
  echo "Backup file not found: $1" >&2
  exit 1
fi

# Validate and fully decompress the archive before sending any SQL to PostgreSQL.
# This prevents a decompression failure from being masked by a successful psql
# process at the end of a POSIX shell pipeline.
gzip -t "$1"
TEMP_SQL=$(mktemp "$BACKUP_DIR/.restore.sql.XXXXXX")
gunzip -c "$1" > "$TEMP_SQL"
echo "Restoring database from $1. Existing objects included in the dump will be dropped and recreated."
psql --set ON_ERROR_STOP=1 "$DATABASE_URL" < "$TEMP_SQL"
echo "Database restore completed successfully."
