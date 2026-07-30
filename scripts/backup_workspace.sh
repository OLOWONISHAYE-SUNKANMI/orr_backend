#!/bin/bash
# Backup script for workspace files (storage/media/config)

set -e

# Load environment variables if .env exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
fi

DATE=$(date +"%Y%m%d_%H%M%S")
WORKSPACE_DIR=${1:-"$PROJECT_ROOT"} # default to project root or passed as arg
FILENAME="orr_workspace_backup_${DATE}.tar.gz"
LOCAL_PATH="/tmp/${FILENAME}"

echo "Starting backup of workspace: ${WORKSPACE_DIR} at ${DATE}"

# Perform the backup, compress it, and encrypt it
echo "Tarring and encrypting workspace..."
tar -czf - -C "${WORKSPACE_DIR}" . | gpg --symmetric --batch --passphrase "${GPG_PASSPHRASE}" --output "${LOCAL_PATH}.gpg"

echo "Workspace backup created and encrypted at ${LOCAL_PATH}.gpg"

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

# Implement retention policy (delete backups older than 4 weeks / 1 month)
echo "Applying retention policy (keeping last 4 weekly backups)..."
if command -v gsutil &> /dev/null; then
    THRESHOLD_DATE=$(date -d "30 days ago" +"%Y%m%d")
    
    gsutil ls "${GCS_BUCKET}/" | grep "orr_workspace_backup" | while read -r line; do
      FILE_DATE=$(echo "$line" | grep -oE '[0-9]{8}_[0-9]{6}' | cut -d'_' -f1)
      if [[ -n "$FILE_DATE" ]] && [[ "$FILE_DATE" < "$THRESHOLD_DATE" ]]; then
          echo "Deleting old workspace backup: $line"
          gsutil rm "$line" || true
      fi
    done
fi

echo "Workspace backup process completed."
