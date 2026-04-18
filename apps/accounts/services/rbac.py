"""RBAC service — role-based access control for the RAG platform."""

import logging
from functools import wraps
from typing import List, Optional

from django.contrib.auth.models import User
from django.db import transaction

from .models import Role, UserRoleBinding, ScopePermission

logger = logging.getLogger(__name__)


def has_role(user: User, role_name: str) -> bool:
    """Check if a user has a specific role (active binding only)."""
    if not user or not user.is_authenticated:
        return False
    return UserRoleBinding.objects.filter(
        user=user, role__name=role_name, role__is_active=True, is_deleted=False
    ).exists()


def get_user_roles(user: User) -> List[str]:
    """Return list of active role names for a user."""
    if not user or not user.is_authenticated:
        return []
    return list(
        UserRoleBinding.objects.filter(
            user=user, role__is_active=True, is_deleted=False
        ).values_list("role__name", flat=True)
    )


def assign_role(user: User, role_name: str, granted_by: Optional[User] = None) -> UserRoleBinding:
    """Assign a role to a user. Idempotent — returns existing binding if already assigned."""
    role = Role.objects.get(name=role_name, is_active=True)
    binding, created = UserRoleBinding.objects.get_or_create(
        user=user, role=role, is_deleted=False,
        defaults={"granted_by": granted_by},
    )
    if created:
        logger.info("Role '%s' assigned to user '%s' by '%s'", role_name, user.username, getattr(granted_by, "username", "system"))
    return binding


def revoke_role(user: User, role_name: str) -> bool:
    """Revoke a role from a user. Returns True if binding was found and removed."""
    deleted_count, _ = UserRoleBinding.objects.filter(
        user=user, role__name=role_name, is_deleted=False
    ).delete()
    if deleted_count:
        logger.info("Role '%s' revoked from user '%s'", role_name, user.username)
    return deleted_count > 0


from django.db import models as db_models


def check_permission(
    user: User,
    action: str,
    scope_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
) -> bool:
    """Check if user has a specific permission through any of their active roles.

    Permission is granted if any of the user's roles has a ScopePermission matching:
      - action (exact)
      - resource_type (exact or '*')
      - scope_type (exact or 'global')
      - resource_id (exact or NULL for wildcard)
    """
    if not user or not user.is_authenticated:
        return False

    role_ids = list(
        UserRoleBinding.objects.filter(
            user=user, role__is_active=True, is_deleted=False
        ).values_list("role_id", flat=True)
    )
    if not role_ids:
        return False

    qs = ScopePermission.objects.filter(role_id__in=role_ids, action=action, is_deleted=False)
    if resource_type:
        qs = qs.filter(db_models.Q(resource_type=resource_type) | db_models.Q(resource_type="*"))
    if scope_type:
        qs = qs.filter(db_models.Q(scope_type=scope_type) | db_models.Q(scope_type="global"))
    if resource_id is not None:
        qs = qs.filter(db_models.Q(resource_id=resource_id) | db_models.Q(resource_id__isnull=True))
    else:
        qs = qs.filter(resource_id__isnull=True)

    return qs.exists()


def require_role(role_names: List[str]):
    """Decorator for Django views that requires at least one of the specified roles.

    Usage:
        @require_role(['operator', 'super_admin'])
        def my_view(request):
            ...
    Returns 401 if not authenticated, 403 if user lacks all required roles.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.http import JsonResponse
                return JsonResponse({"error": "Authentication required"}, status=401)
            if not any(has_role(request.user, rn) for rn in role_names):
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("Insufficient permissions")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
