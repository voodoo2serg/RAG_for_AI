"""Custom Django admin for accounts app — Role, UserRoleBinding, ScopePermission, ApprovalPolicy."""

from django.contrib import admin
from .models import Role, UserRoleBinding, ScopePermission, ApprovalPolicy


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserRoleBinding)
class UserRoleBindingAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "granted_by", "granted_at")
    list_filter = ("role",)
    search_fields = ("user__username", "role__name")
    raw_id_fields = ("user", "role", "granted_by")
    readonly_fields = ("granted_at", "created_at", "updated_at")


@admin.register(ScopePermission)
class ScopePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "action", "resource_type", "scope_type", "resource_id")
    list_filter = ("role", "scope_type", "resource_type")
    search_fields = ("role__name", "action", "resource_type")
    raw_id_fields = ("role",)


@admin.register(ApprovalPolicy)
class ApprovalPolicyAdmin(admin.ModelAdmin):
    list_display = ("scope_type", "resource_type", "required_role", "auto_approve", "max_duration_seconds")
    list_filter = ("scope_type", "auto_approve")
    raw_id_fields = ("required_role",)
