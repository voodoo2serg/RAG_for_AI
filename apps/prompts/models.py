from django.db import models
from apps.core.models import TimeStampedModel

class PromptTemplate(TimeStampedModel):
    name = models.CharField(max_length=255)
    prompt_type = models.CharField(max_length=64)
    content = models.TextField()
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
