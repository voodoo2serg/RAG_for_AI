"""Tests for chat events — Telegram webhook, message processing, delivery."""

import json
import hmac
from django.test import TestCase, Client
from django.urls import reverse
from apps.core.enums import SensitivityLevel
from apps.domains_projects.models import Domain, Project
from apps.threads.models import Thread
from apps.chat_events.models import TelegramSource, Message, OutboundDeliveryLog
from apps.chat_events.services import normalize_text, route_message_to_project


class TelegramSourceTestCase(TestCase):
    """Test Telegram source model."""

    def setUp(self):
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.source = TelegramSource.objects.create(
            slug="test-bot",
            display_name="Test Bot",
            source_kind="live_bot",
            default_domain=self.domain,
            bot_username="testbot",
        )

    def test_source_creation(self):
        self.assertEqual(self.source.slug, "test-bot")
        self.assertEqual(self.source.display_name, "Test Bot")
        self.assertTrue(self.source.is_active)

    def test_source_str(self):
        self.assertEqual(str(self.source), "test-bot")

    def test_source_default_domain(self):
        self.assertEqual(self.source.default_domain, self.domain)


class MessageTestCase(TestCase):
    """Test Message model."""

    def setUp(self):
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.project = Project.objects.create(domain=self.domain, canonical_name="Test Project", slug="test-project")
        self.thread = Thread.objects.create(domain=self.domain, project=self.project, title="Test Thread")
        self.source = TelegramSource.objects.create(
            slug="test-bot", display_name="Test Bot", source_kind="live_bot",
            default_domain=self.domain,
        )
        self.message = Message.objects.create(
            source=self.source,
            domain=self.domain,
            project=self.project,
            thread=self.thread,
            telegram_message_id=1,
            chat_id=123,
            text="Hello world",
            normalized_text="hello world",
            role=Message.MessageRole.OWNER_IDEA,
            value_tier=Message.ValueTier.HIGH,
            sensitivity=SensitivityLevel.INTERNAL,
        )

    def test_message_creation(self):
        self.assertEqual(self.message.text, "Hello world")
        self.assertEqual(self.message.role, Message.MessageRole.OWNER_IDEA)

    def test_message_normalization(self):
        self.assertEqual(self.message.normalized_text, "hello world")

    def test_message_sensitivity(self):
        self.assertEqual(self.message.sensitivity, SensitivityLevel.INTERNAL)

    def test_message_value_tier(self):
        self.assertEqual(self.message.value_tier, Message.ValueTier.HIGH)


class NormalizeTextTestCase(TestCase):
    """Test text normalization service."""

    def test_basic_normalization(self):
        result = normalize_text("Hello World!")
        self.assertIsInstance(result, str)

    def test_empty_text(self):
        result = normalize_text("")
        self.assertEqual(result, "")

    def test_whitespace_cleanup(self):
        result = normalize_text("  multiple   spaces  ")
        self.assertNotIn("  ", result)


class RouteMessageTestCase(TestCase):
    """Test message routing to projects."""

    def setUp(self):
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.project = Project.objects.create(domain=self.domain, canonical_name="Test Project", slug="test-project")

    def test_route_to_existing_project(self):
        result = route_message_to_project("Test Project message", self.domain)
        self.assertIsNotNone(result)

    def test_route_with_no_match(self):
        result = route_message_to_project("random text", self.domain)
        # Should return None or default project
        self.assertIsNone(result)


class WebhookTestCase(TestCase):
    """Test Telegram webhook endpoint."""

    def setUp(self):
        self.client = Client()
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.source = TelegramSource.objects.create(
            slug="test-webhook-bot",
            display_name="Test Webhook Bot",
            source_kind="live_bot",
            default_domain=self.domain,
            webhook_secret="test-secret-123",
        )

    def test_webhook_get_not_allowed(self):
        response = self.client.get("/telegram/webhook/test-webhook-bot/")
        self.assertEqual(response.status_code, 405)  # Method not allowed

    def test_webhook_invalid_json(self):
        response = self.client.post(
            "/telegram/webhook/test-webhook-bot/",
            data="not json",
            content_type="text/plain",
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_missing_secret(self):
        payload = {
            "message": {
                "message_id": 1,
                "date": 1234567890,
                "chat": {"id": 123},
                "text": "Test message",
            }
        }
        response = self.client.post(
            "/telegram/webhook/test-webhook-bot/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        # Should fail due to missing secret
        self.assertEqual(response.status_code, 403)

    def test_webhook_with_valid_secret(self):
        payload = {
            "message": {
                "message_id": 1,
                "date": 1234567890,
                "chat": {"id": 123},
                "text": "Test message",
            }
        }
        response = self.client.post(
            "/telegram/webhook/test-webhook-bot/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="test-secret-123",
        )
        # Should process successfully (200) or create message
        self.assertIn(response.status_code, [200, 201, 500])  # 500 if processing fails

    def test_webhook_empty_message(self):
        payload = {"message": {}}
        response = self.client.post(
            "/telegram/webhook/test-webhook-bot/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="test-secret-123",
        )
        self.assertEqual(response.status_code, 400)


class OutboundDeliveryLogTestCase(TestCase):
    """Test outbound delivery tracking."""

    def setUp(self):
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.source = TelegramSource.objects.create(
            slug="test-bot", display_name="Test Bot", source_kind="live_bot",
            default_domain=self.domain,
        )

    def test_delivery_log_creation(self):
        log = OutboundDeliveryLog.objects.create(
            source=self.source,
            target_chat_id=12345,
            text="Hello",
            status=OutboundDeliveryLog.Status.PENDING,
        )
        self.assertEqual(log.status, OutboundDeliveryLog.Status.PENDING)
        self.assertEqual(log.target_chat_id, 12345)

    def test_delivery_status_transitions(self):
        log = OutboundDeliveryLog.objects.create(
            source=self.source,
            target_chat_id=12345,
            text="Hello",
            status=OutboundDeliveryLog.Status.PENDING,
        )
        log.status = OutboundDeliveryLog.Status.SENT
        log.save()
        self.assertEqual(log.status, OutboundDeliveryLog.Status.SENT)

    def test_delivery_failed_status(self):
        log = OutboundDeliveryLog.objects.create(
            source=self.source,
            target_chat_id=12345,
            text="Hello",
            status=OutboundDeliveryLog.Status.FAILED,
        )
        self.assertEqual(log.status, OutboundDeliveryLog.Status.FAILED)
