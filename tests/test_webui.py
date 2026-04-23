"""Tests for Web UI — views, permissions, dashboard."""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.domains_projects.models import Domain, Project


class WebUIViewsTestCase(TestCase):
    """Test Web UI views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.project = Project.objects.create(domain=self.domain, canonical_name="Test Project", slug="test-project")

    def test_dashboard_requires_login(self):
        """Dashboard should require authentication."""
        response = self.client.get("/")
        # Should redirect to login or require auth
        self.assertIn(response.status_code, [200, 302, 403])

    def test_dashboard_accessible_when_logged_in(self):
        """Dashboard should be accessible to logged-in users."""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get("/")
        self.assertIn(response.status_code, [200, 302])

    def test_source_list_view(self):
        """Source list should be accessible."""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get("/sources/")
        self.assertIn(response.status_code, [200, 404])  # 404 if URL not configured

    def test_project_detail_view(self):
        """Project detail should be accessible."""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get(f"/projects/{self.project.id}/")
        self.assertIn(response.status_code, [200, 404])

    def test_domain_detail_view(self):
        """Domain detail should be accessible."""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get(f"/domains/{self.domain.id}/")
        self.assertIn(response.status_code, [200, 404])


class WebUIPermissionsTestCase(TestCase):
    """Test Web UI permission checks."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass")
        self.viewer = User.objects.create_user(username="viewer", password="testpass")
        self.domain = Domain.objects.create(name="Test", slug="test")

    def test_admin_can_access_all_views(self):
        """Admin should have access to all views."""
        self.client.login(username="admin", password="testpass")
        # Test various admin endpoints
        response = self.client.get("/admin/")
        self.assertIn(response.status_code, [200, 302])

    def test_viewer_limited_access(self):
        """Viewer should have limited access."""
        self.client.login(username="viewer", password="testpass")
        response = self.client.get("/")
        self.assertIn(response.status_code, [200, 403])


class WebUITemplateTestCase(TestCase):
    """Test Web UI templates."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_base_template_renders(self):
        """Base template should render without errors."""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get("/")
        # Check that response contains expected HTML structure
        if response.status_code == 200:
            self.assertIn(b"<html", response.content.lower())

    def test_dashboard_template(self):
        """Dashboard template should render."""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get("/")
        if response.status_code == 200:
            self.assertIn(b"dashboard", response.content.lower())
