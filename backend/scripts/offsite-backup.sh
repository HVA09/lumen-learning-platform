#!/bin/sh
# Upload the newest verified PostgreSQL archive to an encrypted Restic repository.
# This script deliberately does not initialize repositories or delete local backups.
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RESTIC_BACKUP_TAG="${RESTIC_BACKUP_TAG:-lumen-postgres}"
RESTIC_KEEP_DAILY="${RESTIC_KEEP_DAILY:-7}"
RESTIC_KEEP_WEEKLY="${RESTIC_KEEP_WEEKLY:-4}"
RESTIC_KEEP_MONTHLY="${RESTIC_KEEP_MONTHLY:-12}"
RESTIC_KEEP_YEARLY="${RESTIC_KEEP_YEARLY:-3}"

fail() {
  echo "Offsite backup error: $*" >&2
  exit 1
}

require_positive_integer() {
  case "$2" in
    ""|*[!0-9]*|0)
      fail "$1 must be a positive integer."
      ;;
  esac
}

[ -n "${RESTIC_REPOSITORY:-}" ] || fail "RESTIC_REPOSITORY is required."
[ -n "${RESTIC_PASSWORD_FILE:-}" ] || fail "RESTIC_PASSWORD_FILE is required."
[ -s "$RESTIC_PASSWORD_FILE" ] || fail "Restic password file is missing or empty."
[ -d "$BACKUP_DIR" ] || fail "Local backup directory does not exist: $BACKUP_DIR"

require_positive_integer RESTIC_KEEP_DAILY "$RESTIC_KEEP_DAILY"
require_positive_integer RESTIC_KEEP_WEEKLY "$RESTIC_KEEP_WEEKLY"
require_positive_integer RESTIC_KEEP_MONTHLY "$RESTIC_KEEP_MONTHLY"
require_positive_integer RESTIC_KEEP_YEARLY "$RESTIC_KEEP_YEARLY"

# Filenames are UTC/local timestamped as YYYYMMDD_HHMMSS, so lexical order is
# chronological. Avoid GNU-only find options to keep this script portable to Alpine.
LATEST_BACKUP=""
for candidate in "$BACKUP_DIR"/backup_*.sql.gz; do
  [ -f "$candidate" ] || continue
  LATEST_BACKUP="$candidate"
done

if [ -z "$LATEST_BACKUP" ]; then
  echo "No local PostgreSQL backup archive is available yet."
  exit 0
fi

gzip -t "$LATEST_BACKUP"

# Fail closed when the repository is uninitialized, unavailable, or encrypted
# with a different password. Never initialize a remote repository automatically.
restic cat config >/dev/null

snapshots_json=$(restic snapshots --json --tag "$RESTIC_BACKUP_TAG")
printf '%s\n' "$snapshots_json" | jq -e 'type == "array"' >/dev/null \
  || fail "Restic returned invalid snapshot metadata."

# The timestamped archive path is unique per backup. Skip it if this exact archive
# has already been uploaded, including after the sidecar container restarts.
if printf '%s\n' "$snapshots_json" \
  | jq -e --arg source "$LATEST_BACKUP" 'any(.[]; any(.paths[]?; . == $source))' >/dev/null; then
  echo "Latest backup is already present in the encrypted Restic repository: ${LATEST_BACKUP##*/}"
  exit 0
fi

echo "Uploading encrypted offsite backup: ${LATEST_BACKUP##*/}"
restic backup --tag "$RESTIC_BACKUP_TAG" --group-by host,tags "$LATEST_BACKUP"

# All daily archive files have different paths. Group by stable host+tag identity,
# not path, or retention would treat every date as an independent backup set.
restic forget \
  --group-by host,tags \
  --tag "$RESTIC_BACKUP_TAG" \
  --keep-daily "$RESTIC_KEEP_DAILY" \
  --keep-weekly "$RESTIC_KEEP_WEEKLY" \
  --keep-monthly "$RESTIC_KEEP_MONTHLY" \
  --keep-yearly "$RESTIC_KEEP_YEARLY" \
  --prune

# Check repository structure after pruning. This checks metadata, not every data
# pack; schedule a separate full-data check as an operational maintenance task.
restic check

echo "Encrypted offsite backup completed: ${LATEST_BACKUP##*/}"
