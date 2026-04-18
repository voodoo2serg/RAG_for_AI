from django.db import models
from apps.core.models import TimeStampedModel
from apps.core.enums import ScopeType

class WikiSpace(TimeStampedModel):
    scope_type = models.CharField(max_length=32, choices=ScopeType.choices)
    scope_id = models.BigIntegerField()
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("scope_type", "scope_id")]

    def __str__(self):
        return self.name


class WikiPage(TimeStampedModel):
    class PageType(models.TextChoices):
        GLOBAL_OVERVIEW = "global_overview", "Global Overview"
        DOMAIN_OVERVIEW = "domain_overview", "Domain Overview"
        PROJECT_OVERVIEW = "project_overview", "Project Overview"
        ARCHITECTURE = "architecture", "Architecture"
        ANALYSIS = "analysis", "Analysis"
        DECISION_LOG = "decision_log", "Decision Log"
        ARCHIVE_GUIDE = "archive_guide", "Archive Guide"
        OPERATIONS = "operations", "Operations"
        SECRET_REFERENCE = "secret_reference", "Secret Reference"
        CUSTOM = "custom", "Custom"

    wiki_space = models.ForeignKey(WikiSpace, on_delete=models.CASCADE, related_name="pages")
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    page_type = models.CharField(max_length=64, choices=PageType.choices)
    summary = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    current_revision = models.ForeignKey(
        "WikiRevision", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="current_for_page",
        help_text="The currently active revision for this wiki page",
    )

    class Meta:
        unique_together = [("wiki_space", "slug")]

    def __str__(self):
        return self.title


class WikiRevision(TimeStampedModel):
    wiki_page = models.ForeignKey(WikiPage, on_delete=models.CASCADE, related_name="revisions")
    content_text = models.TextField()
    content_format = models.CharField(max_length=32, default="markdown")
    author_type = models.CharField(max_length=32, default="human")
    source_summary_ids = models.JSONField(default=list, blank=True)
    source_knowledge_item_ids = models.JSONField(default=list, blank=True)
    source_message_ids = models.JSONField(default=list, blank=True)


class WikiLink(TimeStampedModel):
    wiki_page = models.ForeignKey(WikiPage, on_delete=models.CASCADE, related_name="links")
    target_type = models.CharField(max_length=64)
    target_id = models.BigIntegerField()
    link_kind = models.CharField(max_length=64)
    label = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
