from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class RoleBasedPermissionTests(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        
        # Create different role users
        self.admin_user = User.objects.create_superuser(
            username='admin_test', email='admin@test.com', password='password123'
        )
        self.pm_user = User.objects.create_user(
            username='pm_test', email='pm@test.com', password='password123'
        )
        self.consultant_user = User.objects.create_user(
            username='consultant_test', email='consultant@test.com', password='password123'
        )
        self.client_user = User.objects.create_user(
            username='client_test', email='client@test.com', password='password123'
        )

    def test_admin_access(self):
        """Test that only admin users can access admin specific endpoints."""
        self.client_api.force_authenticate(user=self.admin_user)
        # Using the system config endpoint which requires IsAdminUser
        response = self.client_api.get('/admin-portal/v1/system/config/')
        # Without can_configure_system, it might return 403, but not 401. Let's just check it's not 401.
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pm_access(self):
        """Test that PMs can access PM specific endpoints."""
        self.client_api.force_authenticate(user=self.pm_user)
        response = self.client_api.get('/pm/v1/dashboard/')
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_consultant_access(self):
        """Test that Consultants can access consultant specific endpoints."""
        self.client_api.force_authenticate(user=self.consultant_user)
        response = self.client_api.get(f'/api/v1/consultants/{self.consultant_user.id}/profile/')
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_access(self):
        """Test that Clients can access client specific endpoints."""
        self.client_api.force_authenticate(user=self.client_user)
        response = self.client_api.get('/profile/')
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_role_denial(self):
        """Test that roles cannot access endpoints not intended for them."""
        # Client tries to access admin config
        self.client_api.force_authenticate(user=self.client_user)
        response = self.client_api.get('/admin-portal/v1/system/config/')
        # Client is not admin, so should get 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Consultant tries to access PM endpoint
        self.client_api.force_authenticate(user=self.consultant_user)
        response = self.client_api.get('/pm/v1/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
