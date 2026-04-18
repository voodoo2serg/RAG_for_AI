from django.db import models
from apps.core.models import TimeStampedModel

class Contact(TimeStampedModel):
    canonical_name = models.CharField(max_length=255)
    aliases = models.JSONField(default=list, blank=True)
    telegram_handle = models.CharField(max_length=255, blank=True)
    phones = models.JSONField(default=list, blank=True)
    emails = models.JSONField(default=list, blank=True)
    role = models.CharField(max_length=255, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.canonical_name
