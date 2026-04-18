from django.db import models
from apps.core.models import TimeStampedModel
from apps.chat_events.models import Message
from apps.domains_projects.models import Project

class Artifact(TimeStampedModel):
    file_key = models.CharField(max_length=512)
    bucket = models.CharField(max_length=128)
    file_type = models.CharField(max_length=64)
    linked_message = models.ForeignKey(Message, null=True, blank=True, on_delete=models.SET_NULL, related_name="artifacts")
    linked_project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="artifacts")
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.file_key
