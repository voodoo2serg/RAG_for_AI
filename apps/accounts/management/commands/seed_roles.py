"""Seed default system roles with scoped permissions."""

from django.core.management.base import BaseCommand
from apps.accounts.models import Role, ScopePermission


DEFAULT_ROLES = [
    {
        "name": "super_admin",
        "description": "Full system access — all permissions on all resources",
        "permissions": [
            {"action": "*", "resource_type": "*", "scope_type": "global"},
        ],
    },
    {
        "name": "operator",
        "description": "Day-to-day operations: manage messages, jobs, sources, wiki, knowledge",
        "permissions": [
            {"action": "view", "resource_type": "message", "scope_type": "global"},
            {"action": "edit", "resource_type": "message", "scope_type": "global"},
            {"action": "view", "resource_type": "wiki", "scope_type": "global"},
            {"action": "edit", "resource_type": "wiki", "scope_type": "global"},
            {"action": "view", "resource_type": "knowledge", "scope_type": "global"},
            {"action": "edit", "resource_type": "knowledge", "scope_type": "global"},
            {"action": "view", "resource_type": "job", "scope_type": "global"},
            {"action": "manage", "resource_type": "job", "scope_type": "global"},
            {"action": "view", "resource_type": "source", "scope_type": "global"},
            {"action": "manage", "resource_type": "source", "scope_type": "global"},
            {"action": "view", "resource_type": "corpus", "scope_type": "global"},
            {"action": "view", "resource_type": "summary", "scope_type": "global"},
            {"action": "view", "resource_type": "domain", "scope_type": "global"},
            {"action": "view", "resource_type": "project", "scope_type": "global"},
            {"action": "view", "resource_type": "dashboard", "scope_type": "global"},
            {"action": "export", "resource_type": "data", "scope_type": "global"},
        ],
    },
    {
        "name": "reviewer",
        "description": "Content review and approval: review queue, knowledge approval, wiki review",
        "permissions": [
            {"action": "view", "resource_type": "message", "scope_type": "global"},
            {"action": "view", "resource_type": "wiki", "scope_type": "global"},
            {"action": "edit", "resource_type": "wiki", "scope_type": "global"},
            {"action": "view", "resource_type": "knowledge", "scope_type": "global"},
            {"action": "approve", "resource_type": "knowledge", "scope_type": "global"},
            {"action": "view", "resource_type": "review_queue", "scope_type": "global"},
            {"action": "approve", "resource_type": "review_queue", "scope_type": "global"},
            {"action": "view", "resource_type": "retrieval", "scope_type": "global"},
        ],
    },
    {
        "name": "analyst",
        "description": "Read-only analytics access: retrieval sessions, diagnostics, corpus stats",
        "permissions": [
            {"action": "view", "resource_type": "message", "scope_type": "global"},
            {"action": "view", "resource_type": "wiki", "scope_type": "global"},
            {"action": "view", "resource_type": "knowledge", "scope_type": "global"},
            {"action": "view", "resource_type": "corpus", "scope_type": "global"},
            {"action": "view", "resource_type": "retrieval", "scope_type": "global"},
            {"action": "view", "resource_type": "dashboard", "scope_type": "global"},
            {"action": "view", "resource_type": "domain", "scope_type": "global"},
            {"action": "view", "resource_type": "project", "scope_type": "global"},
            {"action": "view", "resource_type": "summary", "scope_type": "global"},
        ],
    },
    {
        "name": "viewer",
        "description": "Basic read access to wiki and messages only",
        "permissions": [
            {"action": "view", "resource_type": "message", "scope_type": "global"},
            {"action": "view", "resource_type": "wiki", "scope_type": "global"},
        ],
    },
    {
        "name": "bot_admin",
        "description": "Telegram bot management: register, configure, test sources",
        "permissions": [
            {"action": "view", "resource_type": "source", "scope_type": "global"},
            {"action": "manage", "resource_type": "source", "scope_type": "global"},
            {"action": "view", "resource_type": "domain", "scope_type": "global"},
            {"action": "view", "resource_type": "project", "scope_type": "global"},
        ],
    },
    {
        "name": "security_admin",
        "description": "Security and secret management: view/manage secrets, audit logs, approval policies",
        "permissions": [
            {"action": "view", "resource_type": "secret", "scope_type": "global"},
            {"action": "manage", "resource_type": "secret", "scope_type": "global"},
            {"action": "view", "resource_type": "audit", "scope_type": "global"},
            {"action": "manage", "resource_type": "approval_policy", "scope_type": "global"},
            {"action": "view", "resource_type": "approval_queue", "scope_type": "global"},
            {"action": "approve", "resource_type": "approval_queue", "scope_type": "global"},
        ],
    },
]


class Command(BaseCommand):
    help = "Create default system roles with scoped permissions"

    def handle(self, *args, **options):
        created_count = 0
        perm_count = 0
        for role_def in DEFAULT_ROLES:
            role, created = Role.objects.get_or_create(
                name=role_def["name"],
                defaults={"description": role_def["description"], "is_active": True},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created role: {role.name}"))
            else:
                self.stdout.write(f"  Role exists: {role.name}")
            for perm_def in role_def.get("permissions", []):
                perm, p_created = ScopePermission.objects.get_or_create(
                    role=role,
                    action=perm_def["action"],
                    resource_type=perm_def["resource_type"],
                    scope_type=perm_def.get("scope_type", "global"),
                )
                if p_created:
                    perm_count += 1
        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {created_count} roles created/verified, {perm_count} permissions seeded"
        ))
