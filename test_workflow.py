import os
import django
import sys
from django.conf import settings

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIClient
from client.models import Project
from consultation.models import Consultant, ConsultantJob
from admin_portal.models import AdminRole, AdminProfile, ClientDocument, Client
from django.utils import timezone

def create_mock_users():
    print("--- 1. Creating Mock Users ---")
    # 1. Admin
    admin_user, _ = User.objects.get_or_create(username='test_admin@orr.com', email='test_admin@orr.com')
    admin_user.set_password('password123')
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()
    role, _ = AdminRole.objects.get_or_create(name='super_admin')
    AdminProfile.objects.get_or_create(user=admin_user, role=role)
    print(f"Admin created: {admin_user.email}")

    # 2. PM
    pm_user, _ = User.objects.get_or_create(username='test_pm@orr.com', email='test_pm@orr.com')
    pm_user.set_password('password123')
    pm_user.is_staff = True
    pm_user.save()
    print(f"PM created: {pm_user.email}")

    # 3. Client
    client_user, _ = User.objects.get_or_create(username='test_client@client.com', email='test_client@client.com')
    client_user.set_password('password123')
    client_user.save()
    client_profile, _ = Client.objects.get_or_create(user=client_user, defaults={'company': 'Acme Corp'})
    print(f"Client created: {client_user.email}")

    # 4. Consultant
    consultant_user, _ = User.objects.get_or_create(username='test_consultant@expert.com', email='test_consultant@expert.com')
    consultant_user.set_password('password123')
    consultant_user.save()
    consultant, _ = Consultant.objects.get_or_create(user=consultant_user, defaults={'consultant_number': 'ORR-CONS-TEST', 'status': 'APPROVED'})
    print(f"Consultant created: {consultant_user.email}")

    # 5. Project
    project, _ = Project.objects.get_or_create(
        client=client_profile, 
        name='AI Implementation Strategy',
        defaults={
            'classification': 'TECHNOLOGY',
            'status': 'ACTIVE'
        }
    )
    print(f"Project created: {project.name}")

    return {
        'admin': admin_user,
        'pm': pm_user,
        'client': client_profile,
        'consultant': consultant,
        'project': project
    }

def run_e2e_test():
    users = create_mock_users()
    client = APIClient()

    print("\n--- 2. Executing Workflow API Sequence ---")
    
    # Step 1: PM Requests Consultant
    print("PM requesting consultant...")
    client.force_authenticate(user=users['pm'])
    response = client.post(
        f'/pm/v1/projects/{users["project"].id}/request-consultant/',
        {
            'scope': 'We need an expert to review the machine learning architecture.',
            'deliverables': '1. Architecture Review\n2. Cost Analysis',
            'title': 'AI Architecture Expert Needed'
        },
        format='json'
    )
    assert response.status_code == 200, f"PM Request Failed: {response.content}"
    job_id = response.data['data']['job_id']
    print(f"PM Request successful! Created ConsultantJob ID: {job_id}")

    # Step 2: Admin Assigns Consultant
    print("Admin assigning consultant...")
    client.force_authenticate(user=users['admin'])
    response = client.post(
        f'/admin-portal/v1/consultant-directory/jobs/{job_id}/assign/',
        {'consultant_id': users['consultant'].id},
        format='json'
    )
    assert response.status_code == 200, f"Admin Assign Failed: {response.content}"
    print(f"Admin assigned Consultant {users['consultant'].consultant_number} to Job {job_id}")

    # Step 3: Consultant Accepts & Triggers AI
    print("-> Consultant accepting job (Triggering AI Generation)...")
    client.force_authenticate(user=users['consultant'].user)
    response = client.post(
        f'/api/v1/consultants/jobs/{job_id}/accept/',
        {'feedback': 'I have reviewed the scope. I estimate this will take 40 hours at $150/hr. The timeline is perfectly feasible.'},
        format='json'
    )
    assert response.status_code == 200, f"Consultant Accept Failed: {response.content}"
    print(f"Consultant accepted job! AI is generating the document...")

    # Step 4: Admin Reviews & Approves Draft Document
    print("Admin retrieving AI drafts...")
    client.force_authenticate(user=users['admin'])
    response = client.get('/admin-portal/v1/vault/documents/drafts/')
    assert response.status_code == 200, f"Failed to get drafts: {response.content}"
    drafts = response.data.get('data', [])
    assert len(drafts) > 0, "No draft documents found!"
    doc_id = drafts[-1]['id']
    print(f"Found {len(drafts)} drafts. Approving newest draft (ID: {doc_id})...")

    print("Admin approving draft document...")
    response = client.post(f'/admin-portal/v1/vault/documents/{doc_id}/approve/')
    assert response.status_code == 200, f"Failed to approve document: {response.content}"
    print(f"Document {doc_id} successfully approved and published!")

    print("\n--- 3. Validation ---")
    job = ConsultantJob.objects.get(id=job_id)
    doc = ClientDocument.objects.get(id=doc_id)
    
    print(f"Final Job Status: {job.status} (Expected: ACCEPTED_BY_CONSULTANT)")
    print(f"Final Document Status: is_draft={doc.is_draft}, is_ai_reviewed={doc.is_ai_reviewed}")
    
    if job.status == 'ACCEPTED_BY_CONSULTANT' and not doc.is_draft and doc.is_ai_reviewed:
        print("\n ALL TESTS PASSED SUCCESSFULLY! The entire platform workflow is functioning flawlessly.")
    else:
        print("\nTEST FAILED VALIDATION.")

if __name__ == '__main__':
    run_e2e_test()
