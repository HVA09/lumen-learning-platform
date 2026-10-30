#!/bin/sh
# Daily PostgreSQL backup. Keep only the most recent seven days.
set -eu

umask 077
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/backups/backup_${TIMESTAMP}.sql.gz"

mkdir -p /backups
# --clean/--if-exists lets the restore script replace existing objects safely.
# --no-owner avoids requiring source database roles on the restore target.
pg_dump --clean --if-exists --no-owner "$DATABASE_URL" | gzip > "$BACKUP_FILE"
echo "Backup saved: $BACKUP_FILE"

find /backups -name "backup_*.sql.gz" -type f -mtime +7 -delete
