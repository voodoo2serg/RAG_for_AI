from django.db import models
from apps.core.models import TimeStampedModel
from apps.core.enums import ScopeType
from apps.agent_profiles.models import AgentProfile

class ContextPack(TimeStampedModel):
    scope_type = models.CharField(max_length=32, choices=ScopeType.choices)
    scope_id = models.BigIntegerField()
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    human_readable_text = models.TextField()
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=32, default="draft")
    parent_pack = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

class ContextRule(TimeStampedModel):
    context_pack = models.ForeignKey(ContextPack, on_delete=models.CASCADE, related_name="rules")
    rule_type = models.CharField(max_length=32)
    title = models.CharField(max_length=255)
    body = models.TextField()
    priority = models.IntegerField(default=100)
    is_active = models.BooleanField(default=True)
    applies_when = models.JSONField(default=dict, blank=True)

class ContextGuideline(TimeStampedModel):
    context_pack = models.ForeignKey(ContextPack, on_delete=models.CASCADE, related_name="guidelines")
    title = models.CharField(max_length=255)
    body = models.TextField()
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    is_active = models.BooleanField(default=True)

class ContextSkill(TimeStampedModel):
    context_pack = models.ForeignKey(ContextPack, on_delete=models.CASCADE, related_name="skills")
    skill_key = models.CharField(max_length=128)
    title = models.CharField(max_length=255)
    description = models.TextField()
    invocation_policy = models.CharField(max_length=64, default="manual_or_auto")
    is_enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

class ContextSetting(TimeStampedModel):
    context_pack = models.ForeignKey(ContextPack, on_delete=models.CASCADE, related_name="settings")
    key = models.CharField(max_length=128)
    value_json = models.JSONField(default=dict, blank=True)
    value_text = models.TextField(blank=True)
    value_type = models.CharField(max_length=32, default="json")
    is_active = models.BooleanField(default=True)

class SourceContextBinding(TimeStampedModel):
    source = models.ForeignKey("chat_events.TelegramSource", on_delete=models.CASCADE, related_name="context_bindings")
    context_pack = models.ForeignKey(ContextPack, on_delete=models.CASCADE, related_name="source_bindings")
    is_primary = models.BooleanField(default=True)

class SourceAgentBinding(TimeStampedModel):
    source = models.ForeignKey("chat_events.TelegramSource", on_delete=models.CASCADE, related_name="agent_bindings")
    agent_profile = models.ForeignKey(AgentProfile, on_delete=models.CASCADE, related_name="source_bindings")
    is_primary = models.BooleanField(default=True)
