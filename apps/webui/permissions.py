"""Permission mixins and decorators for Web UI views."""

from functools import wraps
from typing import List

from django.http import HttpResponseForbidden


class RoleRequiredMixin:
    """Mixin for class-based views that requires one or more roles."""

    required_roles: List[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.mixins import LoginRequiredMixin
            return LoginRequiredMixin.as_view()(request, *args, **kwargs)
        from apps.accounts.services.rbac import has_role
        if not any(has_role(request.user, rn) for rn in self.required_roles):
            return HttpResponseForbidden("Insufficient permissions")
        return super().dispatch(request, *args, **kwargs)


class OperatorRequiredMixin(RoleRequiredMixin):
    """Requires 'operator' or 'super_admin' role."""
    required_roles = ["operator", "super_admin"]


class ReviewerRequiredMixin(RoleRequiredMixin):
    """Requires 'reviewer' or 'super_admin' role."""
    required_roles = ["reviewer", "super_admin"]


class AnalystRequiredMixin(RoleRequiredMixin):
    """Requires 'analyst', 'operator', or 'super_admin' role."""
    required_roles = ["analyst", "operator", "super_admin"]


class SecurityAdminRequiredMixin(RoleRequiredMixin):
    """Requires 'security_admin' or 'super_admin' role."""
    required_roles = ["security_admin", "super_admin"]


class BotAdminRequiredMixin(RoleRequiredMixin):
    """Requires 'bot_admin' or 'super_admin' role."""
    required_roles = ["bot_admin", "super_admin"]
