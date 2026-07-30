import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from pm.models import PMProject, PMTask

User = get_user_model()
client = APIClient()

print("--- Starting PM Workflow End-to-End Verification ---")

# 1. Setup Test PM User
email = "testpm_workflow@orr.solutions"
user, created = User.objects.get_or_create(
    username=email,
    defaults={
        "email": email,
        "password": "testpassword123",
        "is_active": True
    }
)
user.is_staff = True
user.save()
from admin_portal.models import AdminProfile
profile, _ = AdminProfile.objects.get_or_create(user=user)
profile.department = 'PM'
profile.save()
print(f"[OK] Created test Project Manager: {email}")

# 2. Authenticate Client
client.force_authenticate(user=user)
print(f"[OK] Authenticated client session.")

# 3. Create a Project (Engagement)
project_payload = {
    "title": "Automated End-to-End Test Engagement",
    "status": "draft",
    "urgency": "normal",
    "client": 106,
    "service_category": "strategy_advisory_compliance",
    "client_name": "TestCorp Inc.",
    "assigned_pm": user.id
}
response = client.post('/pm/v1/projects/', project_payload, format='json')

if response.status_code == 201:
    project_data = response.data.get('data', {}) if 'data' in response.data else response.data
    project_id = project_data.get('id')
    print(f"[OK] Successfully created project '{project_data.get('title')}' with ID: {project_id}")
else:
    print(f"[FAIL] Failed to create project: {response.data}")
    exit(1)

# 4. Create a Task (Deliverable)
task_payload = {
    "title": "Phase 1 Testing Deliverable",
    "task_type": "pm_action",
    "description": "This is an automated workflow test task.",
    "task_structure": "main_task",
    "status": "not_started"
}
response = client.post(f'/pm/v1/projects/{project_id}/tasks/', task_payload, format='json')

if response.status_code == 201:
    task_data = response.data.get('data', {}) if 'data' in response.data else response.data
    task_id = task_data.get('id')
    print(f"[OK] Successfully created task '{task_data.get('title')}' with ID: {task_id}")
else:
    print(f"[FAIL] Failed to create task: {response.data}")
    exit(1)

# 5. Update Task Status (Simulate Drag & Drop)
update_payload = {
    "status": "in_progress"
}
response = client.patch(f'/pm/v1/tasks/{task_id}/', update_payload, format='json')

if response.status_code == 200:
    print(f"[OK] Successfully updated task status to 'in_progress'")
else:
    print(f"[FAIL] Failed to update task: {response.data}")
    exit(1)

# 6. Verify Dashboard Stats
response = client.get('/pm/v1/dashboard/')
if response.status_code == 200:
    dash_data = response.data.get('data', {}) if 'data' in response.data else response.data
    
    # We unwrap twice because of CustomJSONRenderer sometimes wrapping as data: {data: {}}
    if 'data' in dash_data:
        dash_data = dash_data['data']

    print(f"[OK] Dashboard fetch successful.")
    print(f"     Dashboard Projects Total: {dash_data.get('projects', {}).get('total', 0)}")
    print(f"     Dashboard Tasks Completed: {dash_data.get('tasks', {}).get('completed', 0)}")
else:
    print(f"[FAIL] Failed to fetch dashboard: {response.data}")

# 7. Cleanup
print("--- Cleaning up test artifacts ---")
PMTask.objects.filter(id=task_id).delete()
PMProject.objects.filter(id=project_id).delete()
print("[OK] Test artifacts removed.")
print("--- PM Workflow E2E Test Completed Successfully ---")
