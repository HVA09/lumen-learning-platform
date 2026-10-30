#!/bin/sh
# Restore a full PostgreSQL dump. This is destructive and requires an explicit flag.
# Usage:
#   docker compose exec -T backup sh /scripts/restore.sh /backups/backup_XXXXXXXX_XXXXXX.sql.gz --confirm
set -eu

if [ "$#" -ne 2 ] || [ "$2" != "--confirm" ]; then
  echo "Usage: restore.sh <file-under-/backups.sql.gz> --confirm" >&2
  echo "WARNING: this replaces database objects from the selected backup." >&2
  exit 2
fi

case "$1" in
  /backups/backup_*.sql.gz) ;;
  *)
    echo "The backup file must be inside /backups and use the backup_*.sql.gz name." >&2
    exit 2
    ;;
esac

if [ ! -f "$1" ]; then
  echo "Backup file not found: $1" >&2
  exit 1
fi

gzip -t "$1"
echo "Restoring database from $1. Existing objects included in the dump will be dropped and recreated."
gunzip -c "$1" | psql --set ON_ERROR_STOP=1 "$DATABASE_URL"
echo "Database restore completed successfully."
