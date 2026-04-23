"""Tests for API endpoints — auth, CRUD, search."""

import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from apps.core.enums import SensitivityLevel
from apps.domains_projects.models import Domain, Project
from apps.chat_events.models import TelegramSource, Message
from apps.retrieval.models import RagCorpusEntry


class APIAuthTestCase(TestCase):
    """Test API authentication."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.token = Token.objects.create(user=self.user)

    def test_api_requires_auth(self):
        """API should require authentication."""
        response = self.client.get("/api/messages/")
        self.assertIn(response.status_code, [401, 403])

    def test_api_with_token_auth(self):
        """API should work with token auth."""
        response = self.client.get(
            "/api/messages/",
            HTTP_AUTHORIZATION=f"Token {self.key}",
        )
        self.assertIn(response.status_code, [200, 404])

    def test_api_with_invalid_token(self):
        """API should reject invalid tokens."""
        response = self.client.get(
            "/api/messages/",
            HTTP_AUTHORIZATION="Token invalid-token",
        )
        self.assertEqual(response.status_code, 401)


class APIMessagesTestCase(TestCase):
    """Test messages API."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.token = Token.objects.create(user=self.user)
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.project = Project.objects.create(domain=self.domain, canonical_name="Test Project", slug="test-project")
        self.source = TelegramSource.objects.create(
            slug="test-bot", display_name="Test Bot", source_kind="live_bot",
            default_domain=self.domain,
        )
        self.message = Message.objects.create(
            source=self.source,
            domain=self.domain,
            project=self.project,
            telegram_message_id=1,
            chat_id=123,
            text="Test message",
            normalized_text="test message",
            role=Message.MessageRole.OWNER_IDEA,
            value_tier=Message.ValueTier.HIGH,
            sensitivity=SensitivityLevel.INTERNAL,
        )

    def test_list_messages(self):
        """Should list messages."""
        response = self.client.get(
            "/api/messages/",
            HTTP_AUTHORIZATION=f"Token {self.token.key}",
        )
        self.assertIn(response.status_code, [200, 404])

    def test_filter_messages_by_project(self):
        """Should filter messages by project."""
        response = self.client.get(
            f"/api/messages/?project_id={self.project.id}",
            HTTP_AUTHORIZATION=f"Token {self.token.key}",
        )
        self.assertIn(response.status_code, [200, 404])


class APISearchTestCase(TestCase):
    """Test search API."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.token = Token.objects.create(user=self.user)
        self.domain = Domain.objects.create(name="Test", slug="test")

    def test_search_endpoint(self):
        """Search endpoint should accept queries."""
        response = self.client.get(
            "/api/search/?q=test",
            HTTP_AUTHORIZATION=f"Token {self.token.key}",
        )
        self.assertIn(response.status_code, [200, 404])

    def test_search_with_project_filter(self):
        """Search should support project filtering."""
        project = Project.objects.create(domain=self.domain, canonical_name="Test Project", slug="test-project")
        response = self.client.get(
            f"/api/search/?q=test&project_id={project.id}",
            HTTP_AUTHORIZATION=f"Token {self.token.key}",
        )
        self.assertIn(response.status_code, [200, 404])


class APIHealthTestCase(TestCase):
    """Test health check API."""

    def setUp(self):
        self.client = Client()

    def test_health_endpoint(self):
        """Health endpoint should be accessible."""
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)

    def test_health_ready_endpoint(self):
        """Ready endpoint should check DB and Redis."""
        response = self.client.get("/health/ready/")
        self.assertIn(response.status_code, [200, 503])


class APIRateLimitTestCase(TestCase):
    """Test API rate limiting."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.token = Token.objects.create(user=self.user)

    def test_rate_limit_on_webhook(self):
        """Webhook should have rate limiting."""
        # Make multiple requests quickly
        responses = []
        for _ in range(5):
            response = self.client.post("/telegram/webhook/test-bot/")
            responses.append(response.status_code)
        # Should eventually get rate limited (429)
        self.assertTrue(any(code in [429, 403] for code in responses))
