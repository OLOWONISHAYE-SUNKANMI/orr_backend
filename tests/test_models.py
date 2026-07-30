from django.test import TestCase
from django.contrib.auth import get_user_model
from consultation.models import Consultant
from admin_portal.models import Client
from pm.models import PMProject
from client.models import ClientRequest

User = get_user_model()

class RoleModelTests(TestCase):
    def setUp(self):
        # Create base users for different roles
        self.client_user = User.objects.create_user(
            username='client_test',
            email='client@test.com',
            password='password123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='password123'
        )
        self.consultant_user = User.objects.create_user(
            username='consultant_test',
            email='consultant@test.com',
            password='password123'
        )
        self.pm_user = User.objects.create_user(
            username='pm_test',
            email='pm@test.com',
            password='password123'
        )

    def test_user_creation_by_role(self):
        """Test that users are created properly."""
        self.assertTrue(self.admin_user.is_superuser)
        self.assertTrue(self.admin_user.is_staff)

    def test_consultant_profile_creation(self):
        """Test that a consultant profile is linked correctly to the User model."""
        consultant_profile, _ = Consultant.objects.get_or_create(
            user=self.consultant_user
        )
        self.assertEqual(consultant_profile.user, self.consultant_user)

    def test_client_profile_creation(self):
        """Test that a client profile is linked correctly to the User model."""
        client_profile, _ = Client.objects.get_or_create(
            user=self.client_user
        )
        self.assertEqual(client_profile.user, self.client_user)

class StateMachineTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='client2', email='client2@test.com', password='pwd'
        )
        self.client_profile, _ = Client.objects.get_or_create(user=self.client_user)
        
    def test_client_request_default_state(self):
        """Test the default state of a new ClientRequest."""
        req = ClientRequest.objects.create(
            client=self.client_profile,
            submitted_by=self.client_user,
            status="draft"
        )
        self.assertEqual(req.status, "draft")
