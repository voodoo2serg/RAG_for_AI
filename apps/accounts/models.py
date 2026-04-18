from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TimeStampedModel


class Role(TimeStampedModel):
    """System role with scoped permissions."""

    class Meta:
        db_table = "accounts_role"

    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserRoleBinding(TimeStampedModel):
    """Maps a Django user to one or more roles."""

    class Meta:
        db_table = "accounts_user_role_binding"
        unique_together = [("user", "role")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_bindings")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_bindings")
    granted_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="granted_bindings"
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} -> {self.role.name}"


class ScopePermission(TimeStampedModel):
    """Fine-grained permission scoped to role, resource type, and optional resource id."""

    class Meta:
        db_table = "accounts_scope_permission"
        unique_together = [("role", "scope_type", "action", "resource_type")]

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    scope_type = models.CharField(max_length=32, default="global")
    action = models.CharField(max_length=64, help_text="e.g. view, edit, delete, approve, manage")
    resource_type = models.CharField(max_length=64, help_text="e.g. message, wiki, secret, job, source")
    resource_id = models.BigIntegerField(null=True, blank=True, help_text="Optional specific resource id")

    def __str__(self):
        return f"{self.role.name}: {self.action} {self.resource_type}@{self.scope_type}"


class ApprovalPolicy(TimeStampedModel):
    """Policy governing approval workflows for scoped resources."""

    class Meta:
        db_table = "accounts_approval_policy"
        unique_together = [("scope_type", "resource_type")]

    scope_type = models.CharField(max_length=32, default="global")
    resource_type = models.CharField(max_length=64, default="*")
    required_role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="approval_policies")
    auto_approve = models.BooleanField(default=False)
    max_duration_seconds = models.IntegerField(default=86400, help_text="Max grant duration in seconds (default 24h)")
    description = models.TextField(blank=True)

    def __str__(self):
        return f"Policy: {self.resource_type}@{self.scope_type} -> {self.required_role.name}"
