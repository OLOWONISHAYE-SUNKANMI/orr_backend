#!/bin/bash
set -e

# Configuration
# Read from env vars, default to sensible values
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
DB_NAME=${DB_NAME:-"orr_db"}
DB_USER=${DB_USER:-"postgres"}
GCS_BUCKET=${GCS_BUCKET:-"gs://orr-solutions-media/backups"}

# Date formatting for filename
DATE=$(date +"%Y%m%d_%H%M%S")
FILENAME="orr_db_backup_${DATE}.sql.gz"
LOCAL_PATH="/tmp/${FILENAME}"

echo "Starting backup of database: ${DB_NAME} at ${DATE}"

# Perform the backup, compress it, and encrypt it
echo "Dumping and encrypting database..."
PGPASSWORD=${DB_PASSWORD} pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" | gzip | gpg --symmetric --batch --passphrase "${GPG_PASSPHRASE}" --output "${LOCAL_PATH}.gpg"

echo "Backup created and encrypted at ${LOCAL_PATH}.gpg"

# Upload to GCS
if command -v gsutil &> /dev/null; then
    echo "Uploading to Google Cloud Storage..."
    gsutil cp "${LOCAL_PATH}.gpg" "${GCS_BUCKET}/${FILENAME}.gpg"
    
    # cleanup local file after upload
    rm "${LOCAL_PATH}.gpg"
    echo "Backup uploaded successfully and local copy removed."
else
    echo "Warning: gsutil is not installed. Skipping GCS upload."
    echo "Backup saved locally at: ${LOCAL_PATH}.gpg"
fi

# Implement retention policy (delete backups older than 30 days)
echo "Applying retention policy (keeping last 30 daily backups)..."
if command -v gsutil &> /dev/null; then
    # We use a date calculation to find the threshold date
    # In Windows/WSL or Linux, `date -d` works. For this script we assume GNU date.
    THRESHOLD_DATE=$(date -d "30 days ago" +"%Y%m%d")
    
    # We can list and delete older files
    # A simple approach is to try deleting files matching the older date pattern
    # Alternatively, delete files older than 30 days if supported by gsutil lifecycle policies
    # The requirement specifically says "keep last 30 daily".
    gsutil ls "${GCS_BUCKET}/" | while read -r line; do
      FILE_DATE=$(echo "$line" | grep -oE '[0-9]{8}_[0-9]{6}' | cut -d'_' -f1)
      if [[ -n "$FILE_DATE" ]] && [[ "$FILE_DATE" < "$THRESHOLD_DATE" ]]; then
          echo "Deleting old backup: $line"
          gsutil rm "$line" || true
      fi
    done
fi

echo "Backup process completed."
