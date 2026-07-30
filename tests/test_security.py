from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()

class SecurityInjectionTests(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='pw')

    def test_sql_injection_prevention(self):
        """Test SQL injection characters in login form."""
        response = self.client_api.post('/api/v1/auth/login/', {
            'email': "admin@test.com' OR '1'='1",
            'password': "password"
        })
        # Should not crash with 500, should cleanly return 400 or 401
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_auth_bypass(self):
        """Test authentication bypass attempt."""
        response = self.client_api.get('/pm/v1/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
