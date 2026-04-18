from django.db import models
from apps.core.models import TimeStampedModel
from apps.domains_projects.models import Domain, Project

class Thread(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESOLVED = "resolved", "Resolved"
        ARCHIVED = "archived", "Archived"

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="threads")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="threads")
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)
    reconstruction_hint = models.CharField(max_length=255, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    message_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title
