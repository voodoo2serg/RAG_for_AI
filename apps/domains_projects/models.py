from django.db import models
from apps.core.models import TimeStampedModel

class Domain(TimeStampedModel):
    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

class Project(TimeStampedModel):
    class Status(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        ACTIVE = "active", "Active"
        DORMANT = "dormant", "Dormant"
        ARCHIVED = "archived", "Archived"
        MERGED = "merged", "Merged"

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="projects")
    parent_project = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    canonical_name = models.CharField(max_length=255)
    slug = models.SlugField()
    aliases = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)
    importance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = [("domain", "slug")]

    def __str__(self):
        return self.canonical_name

class ProjectRelation(TimeStampedModel):
    class RelationType(models.TextChoices):
        RELATED_TO = "related_to", "Related To"
        DEPENDS_ON = "depends_on", "Depends On"
        SUBPROJECT_OF = "subproject_of", "Subproject Of"
        SHARES_CONTACT_WITH = "shares_contact_with", "Shares Contact With"

    source_project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="outgoing_relations")
    target_project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="incoming_relations")
    relation_type = models.CharField(max_length=64, choices=RelationType.choices)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
