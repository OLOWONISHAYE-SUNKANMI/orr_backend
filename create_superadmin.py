import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from admin_portal.models import AdminRole, AdminProfile

def create_or_update_superadmin():
    email = "superadmin@orr.com"
    password = "password123"

    user, created = User.objects.get_or_create(username=email, email=email)
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.first_name = "Super"
    user.last_name = "Admin"
    user.save()

    # Get or create Super Admin role
    role, _ = AdminRole.objects.get_or_create(
        name="super_admin",
        defaults={"description": "Super Administrator with full platform permissions"}
    )

    # Ensure all super admin permissions are enabled on the role
    role.can_edit_clients = True
    role.can_manage_users = True
    role.can_manage_tickets = True
    role.can_manage_meetings = True
    role.can_view_billing = True
    role.can_manage_settings = True
    role.can_create_content = True
    role.can_publish_content = True
    role.can_view_all_clients = True
    role.can_view_analytics = True
    role.can_view_ai_logs = True
    role.can_manage_roles = True
    role.can_view_audit_logs = True
    role.can_view_security_events = True
    role.can_approve_sensitive_actions = True
    role.can_configure_system = True
    role.save()

    # Link to AdminProfile
    profile, _ = AdminProfile.objects.get_or_create(user=user)
    profile.role = role
    profile.is_active = True
    profile.save()

    print(f"SUCCESS: Superadmin user ready!")
    print(f"Email/Username: {email}")
    print(f"Password: {password}")
    print(f"Role: {role.name}")

if __name__ == "__main__":
    create_or_update_superadmin()
