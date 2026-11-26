#!/usr/bin/env sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-./infrastructure/backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DB_NAME="${POSTGRES_DB:-shoplex}"
DB_USER="${POSTGRES_USER:-shoplex}"
OUTPUT_FILE="${BACKUP_DIR}/shoplex_${DB_NAME}_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"
pg_dump --format=custom --no-owner --no-privileges --username="${DB_USER}" --dbname="${DB_NAME}" --file="${OUTPUT_FILE}"
shasum -a 256 "${OUTPUT_FILE}" > "${OUTPUT_FILE}.sha256"
echo "Backup completed: ${OUTPUT_FILE}"
