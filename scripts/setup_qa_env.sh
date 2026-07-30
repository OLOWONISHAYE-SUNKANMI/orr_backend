#!/bin/bash
# setup_qa_env.sh
# Bootstraps an independent QA environment for Final UAT.

set -e

echo "Setting up Independent QA Environment..."

# Ensure we are in a safe database
export DATABASE_URL=${QA_DATABASE_URL:-"postgres://qa_user:qa_pass@localhost:5432/orr_qa"}

# Run migrations
python manage.py migrate

# Create test roles
echo "Creating roles..."
python manage.py shell -c "
from admin_portal.models import AdminRole
AdminRole.objects.get_or_create(name='super_admin')
AdminRole.objects.get_or_create(name='admin')
AdminRole.objects.get_or_create(name='operator')
AdminRole.objects.get_or_create(name='content_editor')
AdminRole.objects.get_or_create(name='qa_tester')
"

# Create QA test user
echo "Creating QA Tester user..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
from admin_portal.models import AdminProfile, AdminRole
User = get_user_model()
qa_user, created = User.objects.get_or_create(
    username='qa_tester',
    email='qa@orrsolutions.com',
    defaults={'is_staff': True, 'is_superuser': False}
)
if created:
    qa_user.set_password('qapassword123')
    qa_user.save()

role = AdminRole.objects.get(name='qa_tester')
AdminProfile.objects.get_or_create(user=qa_user, defaults={'role': role, 'is_active': True})
"

echo "QA Environment seeded successfully. You can login as 'qa_tester' / 'qapassword123'."
