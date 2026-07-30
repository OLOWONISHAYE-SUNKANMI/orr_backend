# ORR System Disaster Recovery Plan

## Overview
This document outlines the procedures for recovering the ORR platform's database and media assets in the event of data loss, corruption, or catastrophic infrastructure failure. All backups are encrypted using GPG to ensure data-at-rest security.

## 1. GPG Key & Backup Security
To protect sensitive client and operational data, all database and workspace backups are symmetrically encrypted using GPG.
- **Passphrase:** The encryption passphrase is provided via the `GPG_PASSPHRASE` environment variable.
- **Storage:** The `.env` file containing this passphrase must be backed up securely in the organization's offline password manager (e.g., 1Password/Bitwarden).
- **Access Restrictions:** Only Super Admins and the lead DevOps engineer should have access to this passphrase. Without it, the backups are permanently unrecoverable.

## 2. Automated Backups Strategy
The platform automatically generates encrypted database and workspace backups on a scheduled basis via Celery Beat tasks.
- **Database Backups:** Daily at 02:00 AM system time.
- **Workspace Backups:** Weekly on Sundays.
- **Storage Location:** Google Cloud Storage (`gs://orr-solutions-media/backups/`)
- **Format:** `.sql.gz.gpg` and `.tar.gz.gpg`

## 3. Manual Backup Initiation
To trigger a manual database backup:
```bash
# SSH into the production server
cd /var/www/orr-solutions/orr
# Ensure GPG_PASSPHRASE is in the environment
./scripts/backup_db.sh
```

## 4. Restoration Procedure
If the production database is compromised or needs a rollback:
1. Identify the timestamp of the last known good backup from the GCS bucket.
2. Execute the restore script interactively, passing the filename:
```bash
# Ensure GPG_PASSPHRASE is exported in your terminal session
export GPG_PASSPHRASE='your-secure-passphrase'
./scripts/restore_db.sh orr_db_backup_20260728_120000.sql.gz.gpg
```
3. The script will automatically fetch the encrypted backup from GCS, decrypt it locally, forcefully disconnect active PostgreSQL connections, drop the current public schema, and restore the payload.

> [!WARNING]
> Database restoration drops all data written *after* the backup was taken. This action cannot be undone.

## 5. Disaster Scenarios
### Complete Server Loss
If the primary VPS is lost:
1. Provision a new VPS and clone the repository.
2. Re-install PostgreSQL and create the `orr` database and user.
3. Authenticate with Google Cloud SDK on the new server and ensure `.env` contains the `GPG_PASSPHRASE`.
4. Download the latest `.sql.gz.gpg` from `gs://orr-solutions-media/backups/`.
5. Run `./scripts/restore_db.sh <filename>` to decrypt and restore.
6. Run `./scripts/restore_workspace.sh <filename>` (if implemented) or manually decrypt and untar the workspace files to restore media/configs.

### Accidental Data Deletion
Since `AuditLog` captures most entity `post_delete` actions, check the Django Admin Audit Logs first to see if the data can be manually recreated. If not, proceed to use the `restore_db.sh` script to rollback the database.
