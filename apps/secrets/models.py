from django.db import models
from apps.core.models import TimeStampedModel
from apps.core.enums import ScopeType

class SecretRecord(TimeStampedModel):
    scope_type = models.CharField(max_length=32, choices=ScopeType.choices)
    scope_id = models.BigIntegerField()
    label = models.CharField(max_length=255)
    secret_kind = models.CharField(max_length=64)
    encrypted_value = models.BinaryField()
    metadata = models.JSONField(default=dict, blank=True)
    access_policy = models.JSONField(default=dict, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

class SecretAccessLog(TimeStampedModel):
    secret_record = models.ForeignKey(SecretRecord, on_delete=models.CASCADE, related_name="access_logs")
    agent_profile_id = models.BigIntegerField(null=True, blank=True)
    actor_type = models.CharField(max_length=32)
    actor_id = models.BigIntegerField(null=True, blank=True)
    access_mode = models.CharField(max_length=32, default="read")
    reason = models.TextField(blank=True)
    # P2.1: Approval & expiry fields
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Grant expiry time")
    revoked_at = models.DateTimeField(null=True, blank=True, help_text="When grant was revoked")
    revoke_reason = models.TextField(blank=True, help_text="Reason for revocation")
    granted_by_id = models.BigIntegerField(null=True, blank=True, help_text="User who granted access")
