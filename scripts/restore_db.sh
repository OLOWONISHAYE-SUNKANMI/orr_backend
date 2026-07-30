#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════
# ORR Database Restore Script
# Handles both encrypted (.sql.gz.gpg) and plain (.sql.gz) backups
# ═══════════════════════════════════════════════════════════

# Configuration
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
DB_NAME=${DB_NAME:-"orr_db"}
DB_USER=${DB_USER:-"postgres"}
GCS_BUCKET=${GCS_BUCKET:-"gs://orr-solutions-media/backups"}

if [ -z "$1" ]; then
    echo "Usage: ./restore_db.sh <backup_filename_in_gcs_or_local>"
    echo ""
    echo "Supported formats:"
    echo "  .sql.gz.gpg  — GPG-encrypted, gzipped SQL dump (default from backup_db.sh)"
    echo "  .sql.gz      — plain gzipped SQL dump"
    echo ""
    echo "Examples:"
    echo "  ./restore_db.sh orr_db_backup_20260728_120000.sql.gz.gpg"
    echo "  ./restore_db.sh orr_db_backup_20260728_120000.sql.gz"
    exit 1
fi

FILENAME=$1
LOCAL_PATH="/tmp/${FILENAME}"

# Download from GCS if not present locally
if [ ! -f "${LOCAL_PATH}" ]; then
    echo "File not found locally. Attempting to download from GCS..."
    if command -v gsutil &> /dev/null; then
        gsutil cp "${GCS_BUCKET}/${FILENAME}" "${LOCAL_PATH}"
    else
        echo "Error: gsutil is not installed and file is not local."
        exit 1
    fi
fi

echo "Starting restore to database: ${DB_NAME}"
echo "WARNING: This will drop the existing database schema before restoring!"
read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 1
fi

# Determine if the file is GPG-encrypted and decrypt if needed
RESTORE_PATH="${LOCAL_PATH}"
if [[ "${LOCAL_PATH}" == *.gpg ]]; then
    echo "Detected GPG-encrypted backup. Decrypting..."
    if [ -z "${GPG_PASSPHRASE}" ]; then
        echo "Error: GPG_PASSPHRASE environment variable is required for encrypted backups."
        echo "Set it with: export GPG_PASSPHRASE='your-passphrase'"
        exit 1
    fi
    DECRYPTED_PATH="${LOCAL_PATH%.gpg}"
    gpg --decrypt --batch --passphrase "${GPG_PASSPHRASE}" --output "${DECRYPTED_PATH}" "${LOCAL_PATH}"
    echo "Decryption successful."
    RESTORE_PATH="${DECRYPTED_PATH}"
fi

# Terminate active connections and drop/recreate DB
echo "Recreating database..."
PGPASSWORD=${DB_PASSWORD} psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "
    SELECT pg_terminate_backend(pg_stat_activity.pid) 
    FROM pg_stat_activity 
    WHERE pg_stat_activity.datname = '${DB_NAME}' AND pid <> pg_backend_pid();
"
PGPASSWORD=${DB_PASSWORD} psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
PGPASSWORD=${DB_PASSWORD} psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};"

# Restore
echo "Restoring database from ${RESTORE_PATH}..."
gunzip -c "${RESTORE_PATH}" | PGPASSWORD=${DB_PASSWORD} psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}"

# Clean up decrypted file if it was created
if [[ "${LOCAL_PATH}" == *.gpg ]] && [ -f "${DECRYPTED_PATH}" ]; then
    echo "Cleaning up decrypted file..."
    rm -f "${DECRYPTED_PATH}"
fi

echo "Database restore completed successfully."
