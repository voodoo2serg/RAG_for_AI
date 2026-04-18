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


class JobQueueTestCase(TestCase):
    """Test job enqueue, claim, and completion lifecycle."""

    def test_enqueue_and_claim(self):
        from datetime import timedelta
        from django.utils import timezone as django_tz
        job = enqueue_job(
            job_type="test_job",
            payload={"key": "value"},
            idempotency_key="unique-test-key",
        )
        claimed = claim_next_job(job_type="test_job")
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.id, job.id)
        self.assertEqual(claimed.status, "running")
        self.assertEqual(claimed.attempt_count, 1)

    def test_idempotency(self):
        j1 = enqueue_job(job_type="test", idempotency_key="dup-key")
        j2 = enqueue_job(job_type="test", idempotency_key="dup-key")
        self.assertEqual(j1.id, j2.id)

    def test_mark_done(self):
        enqueue_job(job_type="test", idempotency_key="done-key")
        job = claim_next_job(job_type="test")
        mark_done(job)
        job.refresh_from_db()
        self.assertEqual(job.status, "done")
        self.assertIsNotNone(job.finished_at)


class DeliveryLogTestCase(TestCase):
    """Test outbound delivery log creation."""

    def test_create_delivery_log(self):
        from apps.domains_projects.models import Domain
        domain = Domain.objects.create(name="Test", slug="test")
        source = TelegramSource.objects.create(
            slug="test-bot", display_name="Test Bot", source_kind="live_bot",
            default_domain=domain,
        )
        from apps.chat_events.models import OutboundDeliveryLog
        log = OutboundDeliveryLog.objects.create(
            source=source, target_chat_id=12345, text="Hello",
            status=OutboundDeliveryLog.Status.PENDING,
        )
        self.assertEqual(log.status, "pending")
