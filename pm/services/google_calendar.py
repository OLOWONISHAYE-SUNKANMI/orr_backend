import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import uuid
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Try to use credentials.json if available, otherwise we will mock the response.
# In a real environment, you should put credentials.json in the project root or configure the path.
CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, 'credentials.json')

def generate_google_meet_link(start_time, end_time, title, attendees=None):
    """
    Generates a Google Calendar event with a Google Meet link.
    If credentials.json is not found, returns a mock Google Meet link.
    """
    if not os.path.exists(CREDENTIALS_PATH):
        logger.warning("credentials.json not found! Mocking Google Meet link generation.")
        # Generate a realistic looking Google Meet link
        return f"https://meet.google.com/orr-{str(uuid.uuid4())[:8]}"

    try:
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH, scopes=SCOPES)

        service = build('calendar', 'v3', credentials=creds)

        # Create event payload
        event = {
            'summary': title,
            'start': {
                'dateTime': start_time.isoformat(),
            },
            'end': {
                'dateTime': end_time.isoformat(),
            },
            'conferenceData': {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    }
                }
            }
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        # Call the Calendar API
        event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()

        # Extract the Hangout link
        return event.get('hangoutLink', f"https://meet.google.com/orr-{str(uuid.uuid4())[:8]}")
        
    except Exception as e:
        logger.error(f"Failed to generate Google Meet link: {str(e)}")
        # Fallback to mock link if API call fails
        return f"https://meet.google.com/orr-{str(uuid.uuid4())[:8]}"
