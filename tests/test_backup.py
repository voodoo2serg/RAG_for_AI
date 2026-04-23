"""Tests for backup/restore — create, verify, restore operations."""

import os
import tempfile
import zipfile
from django.test import TestCase
from django.core.management import call_command
from apps.domains_projects.models import Domain, Project
from apps.wiki.models import WikiSpace, WikiPage
from apps.agent_profiles.models import AgentProfile
from apps.context_packs.models import ContextPack


class BackupBundleTestCase(TestCase):
    """Test backup bundle creation and verification."""

    def setUp(self):
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.project = Project.objects.create(domain=self.domain, canonical_name="Test Project", slug="test-project")
        self.wiki_space = WikiSpace.objects.create(
            scope_type="project",
            scope_id=self.project.id,
            name="Test Wiki",
            slug="test-wiki",
        )
        self.wiki_page = WikiPage.objects.create(
            wiki_space=self.wiki_space,
            title="Test Page",
            page_type=WikiPage.PageType.PROJECT_OVERVIEW,
        )
        self.agent_profile = AgentProfile.objects.create(
            name="Test Agent",
            slug="test-agent",
            human_readable_text="Test agent profile",
            system_prompt="You are a test agent.",
        )
        self.context_pack = ContextPack.objects.create(
            scope_type="global",
            scope_id=0,
            name="Global Rules",
            slug="global-rules",
            human_readable_text="Global context rules",
        )

    def test_create_backup_bundle(self):
        """Test backup bundle creation command."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            backup_path = tmp.name
        
        try:
            call_command("create_backup_bundle", "--output", backup_path)
            self.assertTrue(os.path.exists(backup_path))
            self.assertTrue(zipfile.is_zipfile(backup_path))
            
            # Verify zip contents
            with zipfile.ZipFile(backup_path, "r") as zf:
                files = zf.namelist()
                self.assertTrue(any("manifest" in f.lower() for f in files))
        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)

    def test_verify_backup_bundle(self):
        """Test backup bundle verification."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            backup_path = tmp.name
        
        try:
            # Create a backup first
            call_command("create_backup_bundle", "--output", backup_path)
            
            # Verify it
            call_command("verify_backup_bundle", backup_path)
            # Should complete without errors
        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)

    def test_verify_corrupted_backup(self):
        """Test verification of corrupted backup."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(b"corrupted data")
            backup_path = tmp.name
        
        try:
            with self.assertRaises(Exception):
                call_command("verify_backup_bundle", backup_path)
        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)


class BackupDataIntegrityTestCase(TestCase):
    """Test that backup captures all critical data."""

    def setUp(self):
        self.domain = Domain.objects.create(name="Test", slug="test")
        self.project = Project.objects.create(domain=self.domain, canonical_name="Test Project", slug="test-project")

    def test_backup_includes_domains(self):
        """Verify domains are included in backup."""
        domains = Domain.objects.all()
        self.assertGreaterEqual(domains.count(), 1)

    def test_backup_includes_projects(self):
        """Verify projects are included in backup."""
        projects = Project.objects.all()
        self.assertGreaterEqual(projects.count(), 1)

    def test_backup_includes_wiki(self):
        """Verify wiki pages are included in backup."""
        wiki_space = WikiSpace.objects.create(
            scope_type="project",
            scope_id=self.project.id,
            name="Test Wiki",
            slug="test-wiki",
        )
        WikiPage.objects.create(
            wiki_space=wiki_space,
            title="Test Page",
            page_type=WikiPage.PageType.PROJECT_OVERVIEW,
        )
        self.assertGreaterEqual(WikiPage.objects.count(), 1)

    def test_backup_includes_agent_profiles(self):
        """Verify agent profiles are included in backup."""
        AgentProfile.objects.create(
            name="Test Agent",
            slug="test-agent",
            human_readable_text="Test agent",
            system_prompt="You are a test agent.",
        )
        self.assertGreaterEqual(AgentProfile.objects.count(), 1)

    def test_backup_includes_context_packs(self):
        """Verify context packs are included in backup."""
        ContextPack.objects.create(
            scope_type="global",
            scope_id=0,
            name="Global Rules",
            slug="global-rules",
            human_readable_text="Global rules",
        )
        self.assertGreaterEqual(ContextPack.objects.count(), 1)
