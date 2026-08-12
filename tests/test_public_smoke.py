"""
Public-endpoint smoke test for the DEFAULT_PERMISSION_CLASSES flip.

After adding a global IsAuthenticated default, genuinely-public endpoints must
still be reachable anonymously (never 401/403), and endpoints that were only
ever implicitly public must now require auth. Run under the test harness so all
tables exist:  manage.py test tests.test_public_smoke
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class PublicEndpointSmokeTests(TestCase):
    """Anonymous requests to public endpoints must not be blocked by auth."""

    def setUp(self):
        self.api = APIClient()

    # (method, path, data): an anonymous call must NOT return 401 or 403.
    PUBLIC = [
        ("get", "/blogs/", None),
        ("post", "/contact/", {}),
        ("post", "/api/auth/login/", {}),
        ("post", "/api/auth/forget-password/", {}),
        ("post", "/api/auth/verify-reset-password/abc/def-token/", {}),
        ("get", "/api/cms/homepage/", None),
        ("post", "/register/", {}),
        ("post", "/client/register/", {}),
        ("post", "/api/v1/consultants/auth/register/", {}),
        ("get", "/pricing-plans/", None),
    ]

    # (method, path): an anonymous call MUST now return 401.
    PROTECTED = [
        ("get", "/profile/"),
        ("get", "/pm/v1/dashboard/"),
    ]

    def test_public_endpoints_not_auth_blocked(self):
        failures = []
        for method, path, data in self.PUBLIC:
            fn = getattr(self.api, method)
            resp = fn(path, data or {}, format="json") if method == "post" else fn(path)
            if resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
                failures.append(f"{method.upper()} {path} -> {resp.status_code}")
        self.assertEqual(failures, [], f"Public endpoints unexpectedly auth-blocked: {failures}")

    def test_protected_endpoints_require_auth(self):
        failures = []
        for method, path in self.PROTECTED:
            resp = getattr(self.api, method)(path)
            if resp.status_code != status.HTTP_401_UNAUTHORIZED:
                failures.append(f"{method.upper()} {path} -> {resp.status_code}")
        self.assertEqual(failures, [], f"Protected endpoints not requiring auth: {failures}")


class AdminEndpointLockdownTests(TestCase):
    """A6: endpoints that previously leaked data must now deny anonymous (401)
    and authenticated non-admin (403) callers.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.api = APIClient()
        User = get_user_model()
        # A plain authenticated user with no AdminProfile => not an admin.
        self.client_user = User.objects.create_user(
            username="lockdown_client", email="lockdown@test.com", password="password123"
        )

    # URL names that resolve to endpoints hardened in A6.
    ADMIN_URL_NAMES = [
        "admin-billing-history",   # billing.AdminBillingHistoryView (was AllowAny)
        "admin-request-list",      # client request admin list (was bare IsAuthenticated)
    ]

    def _resolve(self, name):
        from django.urls import reverse, NoReverseMatch
        try:
            return reverse(name)
        except NoReverseMatch:
            return None

    def test_anonymous_denied(self):
        failures = []
        for name in self.ADMIN_URL_NAMES:
            path = self._resolve(name)
            if path is None:
                failures.append(f"{name}: could not reverse")
                continue
            resp = self.api.get(path)
            if resp.status_code != status.HTTP_401_UNAUTHORIZED:
                failures.append(f"{name} ({path}) anon -> {resp.status_code}")
        self.assertEqual(failures, [], f"Admin endpoints not 401 for anonymous: {failures}")

    def test_authenticated_non_admin_denied(self):
        self.api.force_authenticate(user=self.client_user)
        failures = []
        for name in self.ADMIN_URL_NAMES:
            path = self._resolve(name)
            if path is None:
                continue
            resp = self.api.get(path)
            if resp.status_code != status.HTTP_403_FORBIDDEN:
                failures.append(f"{name} ({path}) client -> {resp.status_code}")
        self.assertEqual(failures, [], f"Admin endpoints not 403 for non-admin client: {failures}")

    def test_cms_comprehensive_write_denied_anonymous(self):
        """Anonymous PUT to a CMS-comprehensive page must be blocked (was open)."""
        path = self._resolve("cms-how-we-operate")
        self.assertIsNotNone(path, "cms-how-we-operate did not reverse")
        # GET stays public.
        get_resp = self.api.get(path)
        self.assertNotIn(
            get_resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
            f"CMS GET should be public, got {get_resp.status_code}",
        )
        # PUT (write) must be denied for anonymous.
        put_resp = self.api.put(path, {"page": {}}, format="json")
        self.assertIn(
            put_resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
            f"CMS anonymous write should be denied, got {put_resp.status_code}",
        )
