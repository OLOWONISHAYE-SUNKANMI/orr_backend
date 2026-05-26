import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from django.conf import settings

class GoogleService:
    def __init__(self, service_type='docs'):
        self.service_type = service_type
        self.credentials = None
        self.service = None
        
        # 1. Try specific env var first (e.g. GOOGLE_CALENDAR_CREDENTIALS_JSON)
        env_var_name = f"GOOGLE_{service_type.upper()}_CREDENTIALS_JSON"
        env_creds = os.environ.get(env_var_name)
        
        # 2. Fallback to primary env var (GOOGLE_DOCS_CREDENTIALS_JSON)
        if not env_creds:
            env_creds = os.environ.get("GOOGLE_DOCS_CREDENTIALS_JSON")
        
        # 3. Final fallback to generic name (GOOGLE_CREDENTIALS_JSON)
        if not env_creds:
            env_creds = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        
        # Helper to build the api service resource
        def try_build(creds):
            try:
                return build(self._get_api_name(), self._get_api_version(), credentials=creds)
            except Exception as build_err:
                print(f"Failed to build Google API client: {build_err}")
                return None

        # Try to load credentials from env first
        if env_creds:
            try:
                creds_info = json.loads(env_creds)
                self.credentials = service_account.Credentials.from_service_account_info(
                    creds_info,
                    scopes=self._get_scopes()
                )
                self.service = try_build(self.credentials)
            except Exception as e:
                print(f"Error loading credentials from environment: {e}")

        # If loading from env failed or didn't yield a working service, try file paths
        if not self.service:
            # 1. Try primary path for service
            primary_path = self._get_credentials_path()
            if os.path.exists(primary_path):
                try:
                    self.credentials = service_account.Credentials.from_service_account_file(
                        primary_path,
                        scopes=self._get_scopes()
                    )
                    self.service = try_build(self.credentials)
                except Exception as e:
                    print(f"Primary key file {primary_path} failed to load/parse: {e}")

        # 2. If primary file failed, try fallback keys
        if not self.service:
            base_path = os.path.join(settings.BASE_DIR, 'google_credentials')
            fallbacks = [
                'google-docs-credentials.json',
                'google-meet-credentials.json',
                'google-email-credentials.json'
            ]
            for fallback_name in fallbacks:
                fallback_path = os.path.join(base_path, fallback_name)
                if os.path.exists(fallback_path) and fallback_path != primary_path:
                    try:
                        self.credentials = service_account.Credentials.from_service_account_file(
                            fallback_path,
                            scopes=self._get_scopes()
                        )
                        self.service = try_build(self.credentials)
                        if self.service:
                            print(f"Successfully self-healed GoogleService using fallback key: {fallback_name}")
                            break
                    except Exception as e:
                        print(f"Fallback key {fallback_name} failed: {e}")

        # 3. Final fallback: Use Application Default Credentials (ADC)
        if not self.service:
            try:
                import google.auth
                self.credentials, _ = google.auth.default(scopes=self._get_scopes())
                self.service = try_build(self.credentials)
            except Exception as e:
                print(f"ADC fallback failed: {e}")

        # If everything failed, raise a clear error that caller functions can catch
        if not self.service:
            raise RuntimeError(f"Could not build Google API service for {service_type}. All credentials files and environment options failed.")

    def _load_from_file(self):
        self.credentials_path = self._get_credentials_path()
        self.credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path,
            scopes=self._get_scopes()
        )

    def _get_credentials_path(self):
        base_path = os.path.join(settings.BASE_DIR, 'google_credentials')
        paths = {
            'docs': 'google-docs-credentials.json',
            'sheets': 'google-docs-credentials.json',
            'drive': 'google-docs-credentials.json',
            'calendar': 'google-calendar-credentials.json',
            'meet': 'google-meet-credentials.json',
            'gmail': 'google-email-credentials.json'
        }
        return os.path.join(base_path, paths.get(self.service_type, 'google-docs-credentials.json'))

    def _get_api_name(self):
        names = {
            'docs': 'docs',
            'sheets': 'sheets',
            'drive': 'drive',
            'calendar': 'calendar',
            'meet': 'meet',
            'gmail': 'gmail',
            'slides': 'slides'
        }
        return names.get(self.service_type)

    def _get_api_version(self):
        versions = {
            'docs': 'v1',
            'sheets': 'v4',
            'drive': 'v3',
            'calendar': 'v3',
            'meet': 'v1',
            'gmail': 'v1',
            'slides': 'v1'
        }
        return versions.get(self.service_type)

    def _get_scopes(self):
        scopes = {
            'docs': ['https://www.googleapis.com/auth/documents'],
            'sheets': ['https://www.googleapis.com/auth/spreadsheets'],
            'drive': ['https://www.googleapis.com/auth/drive'],
            'calendar': ['https://www.googleapis.com/auth/calendar'],
            'meet': ['https://www.googleapis.com/auth/meetings.space.readonly'],
            'gmail': ['https://www.googleapis.com/auth/gmail.send'],
            'slides': ['https://www.googleapis.com/auth/presentations']
        }
        return scopes.get(self.service_type)

    # Docs Methods
    def create_doc(self, title):
        if self.service_type != 'docs':
            raise ValueError("Service must be 'docs' to create a document")
        doc = self.service.documents().create(body={'title': title}).execute()
        return doc

    def create_sheet(self, title):
        if self.service_type != 'sheets':
            raise ValueError("Service must be 'sheets' to create a sheet")
        sheet = self.service.spreadsheets().create(body={'properties': {'title': title}}).execute()
        return sheet

    # Drive Methods
    def share_file(self, file_id, email, role='writer'):
        drive_service = build('drive', 'v3', credentials=self.credentials)
        user_permission = {
            'type': 'user',
            'role': role,
            'emailAddress': email
        }
        return drive_service.permissions().create(
            fileId=file_id,
            body=user_permission,
            fields='id',
        ).execute()

    def make_public(self, file_id, role='reader'):
        drive_service = build('drive', 'v3', credentials=self.credentials)
        permission = {
            'type': 'anyone',
            'role': role,
        }
        return drive_service.permissions().create(
            fileId=file_id,
            body=permission,
            fields='id',
        ).execute()

    def get_file_metadata(self, file_id):
        drive_service = build('drive', 'v3', credentials=self.credentials)
        return drive_service.files().get(fileId=file_id, fields='id, name, mimeType, webViewLink').execute()

    # Calendar Methods
    def create_event(self, summary, start_time, end_time, attendees=None):
        if self.service_type != 'calendar':
            raise ValueError("Service must be 'calendar' to create an event")
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time, 'timeZone': 'UTC'},
            'attendees': [{'email': e} for e in attendees] if attendees else [],
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meet-{summary}-{start_time}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }
        return self.service.events().insert(
            calendarId='primary', 
            body=event,
            conferenceDataVersion=1
        ).execute()

    def create_meet(self, summary, start_time, end_time):
        # Meet can be created via Calendar API with conferenceData
        return self.create_event(summary, start_time, end_time)

    def send_email(self, to, subject, body):
        if self.service_type != 'gmail':
            raise ValueError("Service must be 'gmail' to send email")
        
        import base64
        from email.message import EmailMessage

        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['From'] = 'me'
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        return self.service.users().messages().send(userId='me', body=create_message).execute()
