#!/bin/sh
# Upload every verified PostgreSQL archive not yet present in an encrypted Restic repository.
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
    ""|*[!0-9]*)
      fail "$1 must be a positive integer."
      ;;
  esac
  [ "$2" -gt 0 ] || fail "$1 must be greater than zero."
}

[ -n "${RESTIC_REPOSITORY:-}" ] || fail "RESTIC_REPOSITORY is required."
[ -n "${RESTIC_PASSWORD_FILE:-}" ] || fail "RESTIC_PASSWORD_FILE is required."
[ -s "$RESTIC_PASSWORD_FILE" ] || fail "Restic password file is missing or empty."
[ -d "$BACKUP_DIR" ] || fail "Local backup directory does not exist: $BACKUP_DIR"

require_positive_integer RESTIC_KEEP_DAILY "$RESTIC_KEEP_DAILY"
require_positive_integer RESTIC_KEEP_WEEKLY "$RESTIC_KEEP_WEEKLY"
require_positive_integer RESTIC_KEEP_MONTHLY "$RESTIC_KEEP_MONTHLY"
require_positive_integer RESTIC_KEEP_YEARLY "$RESTIC_KEEP_YEARLY"

# Filenames are timestamped as YYYYMMDD_HHMMSS, so the shell's lexical glob
# order is chronological. Avoid GNU-only find options to keep this portable to Alpine.
HAS_ARCHIVES=0
for candidate in "$BACKUP_DIR"/backup_*.sql.gz; do
  [ -f "$candidate" ] || continue
  HAS_ARCHIVES=1
  break
done

if [ "$HAS_ARCHIVES" -eq 0 ]; then
  echo "No local PostgreSQL backup archive is available yet."
  exit 0
fi

# Validate every local archive before contacting the remote repository or
# uploading any file, so a corrupt local copy cannot cause a partial sync.
for candidate in "$BACKUP_DIR"/backup_*.sql.gz; do
  [ -f "$candidate" ] || continue
  gzip -t "$candidate"
done

# Fail closed when the repository is uninitialized, unavailable, or encrypted
# with a different password. Never initialize a remote repository automatically.
restic cat config >/dev/null

snapshots_json=$(restic snapshots --json --tag "$RESTIC_BACKUP_TAG")
printf '%s\n' "$snapshots_json" | jq -e 'type == "array"' >/dev/null \
  || fail "Restic returned invalid snapshot metadata."

UPLOADED_ANY=0
for candidate in "$BACKUP_DIR"/backup_*.sql.gz; do
  [ -f "$candidate" ] || continue

  # Skip an archive already uploaded, including after a sidecar restart or a
  # period of provider downtime. The local seven-day retention is the retry queue.
  if printf '%s\n' "$snapshots_json" \
    | jq -e --arg source "$candidate" 'any(.[]; any(.paths[]?; . == $source))' >/dev/null; then
    echo "Already present in encrypted Restic repository: ${candidate##*/}"
    continue
  fi

  echo "Uploading encrypted offsite backup: ${candidate##*/}"
  restic backup --tag "$RESTIC_BACKUP_TAG" --group-by host,tags "$candidate"
  UPLOADED_ANY=1
done

if [ "$UPLOADED_ANY" -eq 0 ]; then
  echo "All local PostgreSQL backup archives are already present in Restic."
else
  echo "Uploaded all pending local PostgreSQL backup archives."
fi

# Run retention and repository checks on every successful sync cycle, including
# cycles where all local archives were already present. This retries a previous
# forget/prune failure even when there are no new archives to upload.
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

echo "Encrypted offsite backup synchronization completed."
