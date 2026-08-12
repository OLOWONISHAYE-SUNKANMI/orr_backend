"""Unit tests for the shared RBAC role resolver (`common.roles`).

These assert the documented contract of each resolver function against a matrix
of fixture users — superuser, admin, super_admin, PM, consultant, client, bare
user — plus the two edge cases the resolver explicitly encodes: an *inactive*
AdminProfile is treated as no profile, and an active AdminProfile with no role
is not an admin (but is still a non-PM admin).
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from common import roles
from admin_portal.models import AdminProfile, AdminRole
from client.models import Profile as ClientProfile
from consultation.models import Consultant

User = get_user_model()


class RoleResolverTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        import threading

        # The client app's `create_profiles` post_save signal auto-attaches a
        # client.Profile (and a CRM Client) to every newly-created *non-staff*
        # user. Left unchecked it would give our admin/pm/consultant fixtures a
        # stray client.Profile and make `is_client` true for them. Suppress it
        # with the app's own thread-local escape hatch so each fixture carries
        # exactly the profile we attach, isolating the resolver under test.
        threading.current_thread().skip_auto_client_creation = True
        try:
            cls.admin_role = AdminRole.objects.create(name="admin")
            cls.super_role = AdminRole.objects.create(name="super_admin")

            # 1. Superuser — no AdminProfile at all.
            cls.superuser = User.objects.create_superuser(
                username="root", email="root@orr.com", password="x"
            )

            # 2. Regular admin — active profile, role assigned, non-PM department.
            cls.admin = User.objects.create_user(username="admin1", email="a@orr.com", password="x")
            AdminProfile.objects.create(
                user=cls.admin, role=cls.admin_role, department="Operations", is_active=True
            )

            # 3. Super admin — active profile whose role.name == "super_admin".
            cls.super_admin = User.objects.create_user(username="sa1", email="sa@orr.com", password="x")
            AdminProfile.objects.create(
                user=cls.super_admin, role=cls.super_role, department="Executive", is_active=True
            )

            # 4. PM — active profile in the "PM" department (also has a role).
            cls.pm = User.objects.create_user(username="pm1", email="pm@orr.com", password="x")
            AdminProfile.objects.create(
                user=cls.pm, role=cls.admin_role, department="PM", is_active=True
            )

            # 5. Consultant — has a consultation.Consultant.
            cls.consultant = User.objects.create_user(username="c1", email="c@orr.com", password="x")
            Consultant.objects.create(user=cls.consultant, consultant_number="CONS-0001")

            # 6. Client — authoritative signal is client.Profile.
            cls.client_user = User.objects.create_user(username="cl1", email="cl@orr.com", password="x")
            ClientProfile.objects.create(user=cls.client_user)

            # 7. Bare user — authenticated, but no profile of any kind.
            cls.bare = User.objects.create_user(username="bare1", email="bare@orr.com", password="x")

            # Edge A: inactive AdminProfile — must be treated exactly like "no profile".
            cls.inactive_admin = User.objects.create_user(username="ia1", email="ia@orr.com", password="x")
            AdminProfile.objects.create(
                user=cls.inactive_admin, role=cls.admin_role, department="Operations", is_active=False
            )

            # Edge B: active AdminProfile with NO role — not an admin, but is a non-PM admin.
            cls.roleless_admin = User.objects.create_user(username="ra1", email="ra@orr.com", password="x")
            AdminProfile.objects.create(
                user=cls.roleless_admin, role=None, department="Support", is_active=True
            )
        finally:
            del threading.current_thread().skip_auto_client_creation

    # ---- get_admin_profile -------------------------------------------------

    def test_get_admin_profile_returns_active_profile(self):
        self.assertIsNotNone(roles.get_admin_profile(self.admin))
        self.assertEqual(roles.get_admin_profile(self.admin).user_id, self.admin.id)

    def test_get_admin_profile_none_for_inactive(self):
        self.assertIsNone(roles.get_admin_profile(self.inactive_admin))

    def test_get_admin_profile_none_for_no_profile(self):
        # `bare` is non-staff and had client auto-creation suppressed, so it has
        # no profile of any kind. (A superuser is NOT a valid case here: the
        # admin_portal `create_admin_profile` signal auto-attaches an AdminProfile
        # to every staff/superuser — is_admin(superuser) still holds via the
        # is_superuser short-circuit regardless.)
        self.assertIsNone(roles.get_admin_profile(self.bare))

    # ---- is_admin ----------------------------------------------------------

    def test_is_admin(self):
        self.assertTrue(roles.is_admin(self.superuser))
        self.assertTrue(roles.is_admin(self.admin))
        self.assertTrue(roles.is_admin(self.super_admin))
        self.assertTrue(roles.is_admin(self.pm))  # PM has a role assigned
        self.assertFalse(roles.is_admin(self.consultant))
        self.assertFalse(roles.is_admin(self.client_user))
        self.assertFalse(roles.is_admin(self.bare))
        self.assertFalse(roles.is_admin(self.inactive_admin))  # inactive => no profile
        self.assertFalse(roles.is_admin(self.roleless_admin))  # active but role is None

    # ---- is_super_admin ----------------------------------------------------

    def test_is_super_admin(self):
        self.assertTrue(roles.is_super_admin(self.superuser))
        self.assertTrue(roles.is_super_admin(self.super_admin))
        self.assertFalse(roles.is_super_admin(self.admin))
        self.assertFalse(roles.is_super_admin(self.pm))
        self.assertFalse(roles.is_super_admin(self.roleless_admin))
        self.assertFalse(roles.is_super_admin(self.consultant))
        self.assertFalse(roles.is_super_admin(self.client_user))
        self.assertFalse(roles.is_super_admin(self.bare))

    # ---- is_pm -------------------------------------------------------------

    def test_is_pm(self):
        self.assertTrue(roles.is_pm(self.superuser))
        self.assertTrue(roles.is_pm(self.pm))
        self.assertFalse(roles.is_pm(self.admin))
        self.assertFalse(roles.is_pm(self.super_admin))
        self.assertFalse(roles.is_pm(self.roleless_admin))
        self.assertFalse(roles.is_pm(self.inactive_admin))  # would-be PM but inactive
        self.assertFalse(roles.is_pm(self.consultant))
        self.assertFalse(roles.is_pm(self.client_user))
        self.assertFalse(roles.is_pm(self.bare))

    # ---- is_non_pm_admin ---------------------------------------------------

    def test_is_non_pm_admin(self):
        self.assertTrue(roles.is_non_pm_admin(self.superuser))
        self.assertTrue(roles.is_non_pm_admin(self.admin))
        self.assertTrue(roles.is_non_pm_admin(self.super_admin))
        self.assertTrue(roles.is_non_pm_admin(self.roleless_admin))  # dept != PM, role irrelevant
        self.assertFalse(roles.is_non_pm_admin(self.pm))  # PM is excluded by design
        self.assertFalse(roles.is_non_pm_admin(self.inactive_admin))
        self.assertFalse(roles.is_non_pm_admin(self.consultant))
        self.assertFalse(roles.is_non_pm_admin(self.client_user))
        self.assertFalse(roles.is_non_pm_admin(self.bare))

    # ---- is_client ---------------------------------------------------------

    def test_is_client(self):
        self.assertTrue(roles.is_client(self.client_user))
        self.assertFalse(roles.is_client(self.admin))
        self.assertFalse(roles.is_client(self.pm))
        self.assertFalse(roles.is_client(self.consultant))
        self.assertFalse(roles.is_client(self.superuser))
        self.assertFalse(roles.is_client(self.bare))

    # ---- is_consultant -----------------------------------------------------

    def test_is_consultant(self):
        self.assertTrue(roles.is_consultant(self.consultant))
        self.assertFalse(roles.is_consultant(self.admin))
        self.assertFalse(roles.is_consultant(self.pm))
        self.assertFalse(roles.is_consultant(self.client_user))
        self.assertFalse(roles.is_consultant(self.superuser))
        self.assertFalse(roles.is_consultant(self.bare))

    # ---- anonymous / None guards ------------------------------------------

    def test_anonymous_user_is_never_a_role(self):
        anon = AnonymousUser()
        for fn in (
            roles.is_admin,
            roles.is_super_admin,
            roles.is_pm,
            roles.is_non_pm_admin,
            roles.is_client,
            roles.is_consultant,
        ):
            self.assertFalse(fn(anon), f"{fn.__name__} should be False for AnonymousUser")
        self.assertIsNone(roles.get_admin_profile(anon))

    def test_none_user_is_never_a_role(self):
        for fn in (
            roles.is_admin,
            roles.is_super_admin,
            roles.is_pm,
            roles.is_non_pm_admin,
            roles.is_client,
            roles.is_consultant,
        ):
            self.assertFalse(fn(None), f"{fn.__name__} should be False for None")
        self.assertIsNone(roles.get_admin_profile(None))
