import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from admin_portal.models import Client, Meeting, Content, ClientDocument, SystemNotification, AdminProfile
from client.models import Project, Profile as ClientProfile
from consultation.models import Consultant, ConsultantJob
from payment.models import Invoice, Subscription

def clean_dummy_data():
    print("--- 1. Cleaning Dummy CMS Content ---")
    dummy_titles = [
        'Customer Experience Optimization',
        'Risk Management Framework',
        'Market Expansion Strategy',
        'Technology Infrastructure Audit',
        'Financial Performance Review',
        'Operational Efficiency Assessment',
        'Digital Transformation Roadmap',
        'Q4 Strategic Analysis Report'
    ]
    deleted_content, _ = Content.objects.filter(title__in=dummy_titles).delete()
    print(f"Deleted {deleted_content} dummy CMS articles/reports.")

    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("UPDATE admin_portal_systemnotification SET related_meeting_id = NULL WHERE related_meeting_id IN (SELECT id FROM admin_portal_meeting WHERE agenda LIKE '%Strategic consultation session%' OR agenda LIKE '%Completed consultation%');")
        cursor.execute("DELETE FROM admin_portal_meeting WHERE agenda LIKE '%Strategic consultation session%' OR agenda LIKE '%Completed consultation%';")
        deleted_meetings = cursor.rowcount
    print(f"Deleted {deleted_meetings} dummy seed meetings.")

    print("\n--- 3. Cleaning Dummy Seed Users & Clients ---")
    # Preserve important accounts
    preserve_emails = [
        'superadmin@orr.com',
        'test_admin@orr.com',
        'test_pm@orr.com',
        'test_client@client.com',
        'test_consultant@expert.com',
    ]
    
    dummy_usernames = [
        'john_consultant', 'sarah_consultant', 'mike_consultant',
        'testpm@example.com', 'newpm@example.com', 'weakpm@example.com'
    ]
    
    deleted_users, _ = User.objects.filter(username__in=dummy_usernames).delete()
    print(f"Deleted {deleted_users} dummy seed users.")

    # Clean up empty or orphan clients (company='N/A' or user is None)
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM consultation_consultantjob WHERE project_id IN (SELECT id FROM client_project WHERE client_id IN (SELECT id FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user)));")
        cursor.execute("DELETE FROM client_project WHERE client_id IN (SELECT id FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user));")
        cursor.execute("DELETE FROM admin_portal_aiconversation WHERE client_id IN (SELECT id FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user));")
        cursor.execute("UPDATE admin_portal_systemnotification SET related_ticket_id = NULL WHERE related_ticket_id IN (SELECT id FROM admin_portal_ticket WHERE client_id IN (SELECT id FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user)));")
        cursor.execute("UPDATE admin_portal_systemnotification SET related_client_id = NULL WHERE related_client_id IN (SELECT id FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user));")
        cursor.execute("UPDATE admin_portal_systemnotification SET related_meeting_id = NULL WHERE related_meeting_id IN (SELECT id FROM admin_portal_meeting WHERE client_id IN (SELECT id FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user)));")
        cursor.execute("DELETE FROM admin_portal_clientdocument WHERE client_id IN (SELECT id FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user));")
        cursor.execute("DELETE FROM admin_portal_ticketmessage WHERE ticket_id IN (SELECT id FROM admin_portal_ticket WHERE client_id IN (SELECT id FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user)));")
        cursor.execute("DELETE FROM admin_portal_ticket WHERE client_id IN (SELECT id FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user));")
        cursor.execute("DELETE FROM admin_portal_meeting WHERE client_id IN (SELECT id FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user));")
        cursor.execute("DELETE FROM admin_portal_client WHERE company = 'N/A' OR user_id IS NULL OR user_id NOT IN (SELECT id FROM auth_user);")
        orphan_clients = cursor.rowcount
    print(f"Deleted {orphan_clients} incomplete/dummy client records.")

    print("\n--- Database Cleanup Summary ---")
    print('Remaining Users:', User.objects.count())
    print('Remaining Clients:', Client.objects.count())
    print('Remaining Meetings:', Meeting.objects.count())
    print('Remaining CMS Content:', Content.objects.count())
    print('Remaining Vault Documents:', ClientDocument.objects.count())
    print('Remaining Projects:', Project.objects.count())
    print('Remaining Consultant Jobs:', ConsultantJob.objects.count())

if __name__ == '__main__':
    clean_dummy_data()
