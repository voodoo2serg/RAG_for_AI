from django.db import models
from apps.core.models import TimeStampedModel

class AgentProfile(TimeStampedModel):
    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(unique=True)
    purpose = models.TextField(blank=True)
    human_readable_text = models.TextField()
    system_prompt = models.TextField()
    autonomy_level = models.CharField(max_length=32, default="advisory")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class AgentProfileRule(TimeStampedModel):
    agent_profile = models.ForeignKey(AgentProfile, on_delete=models.CASCADE, related_name="rules")
    rule_type = models.CharField(max_length=32)
    title = models.CharField(max_length=255)
    body = models.TextField()
    priority = models.IntegerField(default=100)
    is_active = models.BooleanField(default=True)

class AgentProfilePermission(TimeStampedModel):
    agent_profile = models.ForeignKey(AgentProfile, on_delete=models.CASCADE, related_name="permissions")
    action_key = models.CharField(max_length=128)
    allow = models.BooleanField(default=False)
    conditions = models.JSONField(default=dict, blank=True)
