from django.db import models
from apps.core.models import TimeStampedModel

class ArchiveImportJob(TimeStampedModel):
    status = models.CharField(max_length=32, default="queued")
    source_path = models.CharField(max_length=512, blank=True)
    total_messages = models.IntegerField(default=0)
    processed_messages = models.IntegerField(default=0)
    imported_artifacts = models.IntegerField(default=0)
    summary = models.TextField(blank=True)
