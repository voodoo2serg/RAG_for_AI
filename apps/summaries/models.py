from django.db import models
from apps.core.models import TimeStampedModel
from apps.domains_projects.models import Domain, Project
from apps.threads.models import Thread

class Summary(TimeStampedModel):
    class SummaryLevel(models.TextChoices):
        THREAD = "thread", "Thread"
        PROJECT = "project", "Project"
        MONTHLY = "monthly", "Monthly"
        GLOBAL = "global", "Global"

    summary_level = models.CharField(max_length=32, choices=SummaryLevel.choices)
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL)
    thread = models.ForeignKey(Thread, null=True, blank=True, on_delete=models.SET_NULL)
    summary_text = models.TextField()
    source_message_ids = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    version = models.PositiveIntegerField(default=1)
