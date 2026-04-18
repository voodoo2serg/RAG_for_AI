from django.db import models
from apps.core.models import TimeStampedModel

class JobQueue(TimeStampedModel):
    job_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, default="queued")
    priority = models.IntegerField(default=100)
    available_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_text = models.TextField(blank=True)
