# Google Workspace Setup Guide

ORR Solutions integrates with Google Workspace for core operational functionality, including SSO (Single Sign-On) via Google OAuth2, Google Meet integration for client consultations, and Google Cloud Storage (GCS) for secure Vault document storage and backups.

## 1. Google Cloud Console Initial Setup
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com).
2. Create a new project named `orr-solutions-prod`.
3. Enable the following APIs:
   - Google Drive API
   - Google Calendar API
   - Admin SDK API
   - Google Cloud Storage JSON API

## 2. OAuth 2.0 & Single Sign-On Setup
1. In the GCP Console, go to **APIs & Services** > **Credentials**.
2. Configure the **OAuth consent screen**:
   - User Type: Internal (if restricted to ORR domain) or External (if clients use Google to log in).
   - App Name: ORR Solutions
   - User Support Email: support@orrsolutions.com
3. Create **OAuth client ID** credentials:
   - Application type: Web application
   - Authorized redirect URIs:
     - `https://admin.orrsolutions.com/api/auth/google/callback`
     - `https://client.orrsolutions.com/api/auth/google/callback`
4. Copy the **Client ID** and **Client Secret**.
5. Update your backend `.env` file:
   ```env
   GOOGLE_OAUTH_CLIENT_ID="your_client_id"
   GOOGLE_OAUTH_CLIENT_SECRET="your_client_secret"
   ```

## 3. Service Account Setup (For Backups & Vault)
1. Go to **IAM & Admin** > **Service Accounts**.
2. Create a new service account (e.g., `orr-backend-service@orr-solutions-prod.iam.gserviceaccount.com`).
3. Grant the following roles:
   - **Storage Object Admin** (for Vault and Backups)
4. Click into the service account, go to **Keys** > **Add Key** > **Create new key** (JSON format).
5. Download the JSON file securely. This file is highly sensitive.
6. Rename it to `google-credentials.json` and place it in the secure backend directory.
7. Update `.env`:
   ```env
   GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/google-credentials.json"
   GCS_BUCKET_NAME="orr-solutions-prod-storage"
   ```

## 4. Google Cloud Storage (GCS) Bucket Setup
1. Go to **Cloud Storage** > **Buckets**.
2. Create a new bucket named `orr-solutions-prod-storage`.
3. Choose a region close to your primary user base (e.g., `europe-west4`).
4. Ensure **Uniform access control** is enabled.
5. Ensure the bucket is **Private** (Not public). All file access must be proxied through the Django backend for authorization.

## 5. Google Calendar / Meet Integration
Consultation meetings generate automated Google Meet links.
1. The Service Account created in Step 3 needs **Domain-Wide Delegation**.
2. In Google Workspace Admin Console (`admin.google.com`), go to **Security** > **API Controls** > **Domain-wide Delegation**.
3. Add a new API client using the Service Account's Client ID.
4. Grant the following OAuth scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/calendar.events`
5. In the backend `.env`, specify the admin email to impersonate for calendar event creation:
   ```env
   GOOGLE_CALENDAR_DELEGATED_USER="admin@orrsolutions.com"
   ```
