#!/bin/sh
# Daily PostgreSQL backup. Keep only the most recent seven days.
set -eu

umask 077
BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.sql.gz"
TEMP_SQL=""
TEMP_GZ=""

cleanup() {
  if [ -n "$TEMP_SQL" ]; then
    rm -f "$TEMP_SQL"
  fi
  if [ -n "$TEMP_GZ" ]; then
    rm -f "$TEMP_GZ"
  fi
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

mkdir -p "$BACKUP_DIR"
TEMP_SQL=$(mktemp "$BACKUP_DIR/.backup_${TIMESTAMP}.sql.XXXXXX")
TEMP_GZ=$(mktemp "$BACKUP_DIR/.backup_${TIMESTAMP}.sql.gz.XXXXXX")

# Never write directly to the final filename: with POSIX sh, a failing pg_dump
# in a pipeline can be hidden by a successful gzip exit code. Build and verify
# temporary files first, then atomically publish the completed archive.
pg_dump --clean --if-exists --no-owner "$DATABASE_URL" > "$TEMP_SQL"
gzip -c "$TEMP_SQL" > "$TEMP_GZ"
gzip -t "$TEMP_GZ"
mv "$TEMP_GZ" "$BACKUP_FILE"
TEMP_GZ=""
rm -f "$TEMP_SQL"
TEMP_SQL=""

echo "Backup saved: $BACKUP_FILE"

# Prune old backups only after the new backup has been fully published.
find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime +7 -delete
