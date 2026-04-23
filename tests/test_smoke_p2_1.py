"""End-to-end smoke tests for the RAG pipeline — P2.1 regression safety net."""

from django.test import TestCase, override_settings
from django.contrib.auth.models import User

from apps.accounts.services.rbac import has_role, assign_role, check_permission
from apps.accounts.models import Role
from apps.jobs.services.runner import enqueue_job, claim_next_job, mark_done
from apps.chat_events.models import TelegramSource
from apps.retrieval.models import RagCorpusEntry


class RBACTestCase(TestCase):
    """Test RBAC role assignment and permission checking."""

    def setUp(self):
        self.role = Role.objects.create(name="operator", description="Operator", is_active=True)
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_assign_and_check_role(self):
        assign_role(self.user, "operator")
        self.assertTrue(has_role(self.user, "operator"))
        self.assertFalse(has_role(self.user, "super_admin"))

    def test_revoke_role(self):
        assign_role(self.user, "operator")
        from apps.accounts.services.rbac import revoke_role
        revoke_role(self.user, "operator")
        self.assertFalse(has_role(self.user, "operator"))

    def test_get_user_roles(self):
        assign_role(self.user, "operator")
        from apps.accounts.services.rbac import get_user_roles
        roles = get_user_roles(self.user)
        self.assertIn("operator", roles)

    def test_unauthenticated_user_has_no_roles(self):
        anon = User(username="anon", is_anonymous=True)
        anon.is_authenticated = False
        self.assertFalse(has_role(anon, "operator"))
