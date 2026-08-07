from django.core.management.base import BaseCommand
from admin_portal.models import AdminRole


class Command(BaseCommand):
    help = 'Setup default admin roles'

    def handle(self, *args, **options):
        # Create Super Admin role
        super_admin, created = AdminRole.objects.get_or_create(
            name='super_admin',
            defaults={
                'description': 'Full system access with all permissions',
                'can_manage_users': True,
                'can_view_all_clients': True,
                'can_edit_clients': True,
                'can_manage_tickets': True,
                'can_manage_meetings': True,
                'can_create_content': True,
                'can_publish_content': True,
                'can_view_analytics': True,
                'can_view_billing': True,
                'can_manage_settings': True,
                'can_view_ai_logs': True,
            }
        )
        

        # Create Admin role
        admin, created = AdminRole.objects.get_or_create(
            name='admin',
            defaults={
                'description': 'General admin access without user management',
                'can_manage_users': False,
                'can_view_all_clients': True,
                'can_edit_clients': True,
                'can_manage_tickets': True,
                'can_manage_meetings': True,
                'can_create_content': True,
                'can_publish_content': True,
                'can_view_analytics': True,
                'can_view_billing': True,
                'can_manage_settings': False,
                'can_view_ai_logs': True,
            }
        )
        
        # Create Operator role
        operator, created = AdminRole.objects.get_or_create(
            name='operator',
            defaults={
                'description': 'Support and operations staff',
                'can_manage_users': False,
                'can_view_all_clients': True,
                'can_edit_clients': False,
                'can_manage_tickets': True,
                'can_manage_meetings': True,
                'can_create_content': False,
                'can_publish_content': False,
                'can_view_analytics': False,
                'can_view_billing': False,
                'can_manage_settings': False,
                'can_view_ai_logs': False,
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created default admin roles')
        )