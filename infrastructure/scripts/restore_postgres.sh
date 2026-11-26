#!/usr/bin/env sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <path-to-backup.dump>"
  exit 1
fi

BACKUP_FILE="$1"
DB_NAME="${POSTGRES_DB:-shoplex}"
DB_USER="${POSTGRES_USER:-shoplex}"

if [ -f "${BACKUP_FILE}.sha256" ]; then
  shasum -a 256 -c "${BACKUP_FILE}.sha256"
fi

pg_restore --clean --if-exists --no-owner --no-privileges --username="${DB_USER}" --dbname="${DB_NAME}" "${BACKUP_FILE}"
echo "Restore completed into database: ${DB_NAME}"
