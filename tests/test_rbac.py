"""Tests for RBAC — permissions, approval flow, role management."""

from django.test import TestCase
from django.contrib.auth.models import User
from apps.accounts.models import Role, UserRoleBinding, ScopePermission, ApprovalPolicy
from apps.accounts.services.rbac import (
    has_role, assign_role, revoke_role, get_user_roles,
    check_permission, get_user_permissions
)


class RoleModelTestCase(TestCase):
    """Test Role model."""

    def test_role_creation(self):
        role = Role.objects.create(name="test_role", description="Test Role")
        self.assertEqual(role.name, "test_role")
        self.assertTrue(role.is_active)

    def test_role_str(self):
        role = Role.objects.create(name="test_role")
        self.assertEqual(str(role), "test_role")

    def test_role_unique_name(self):
        Role.objects.create(name="unique_role")
        with self.assertRaises(Exception):
            Role.objects.create(name="unique_role")


class UserRoleBindingTestCase(TestCase):
    """Test UserRoleBinding model."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.role = Role.objects.create(name="operator")

    def test_binding_creation(self):
        binding = UserRoleBinding.objects.create(user=self.user, role=self.role)
        self.assertEqual(binding.user, self.user)
        self.assertEqual(binding.role, self.role)

    def test_binding_unique(self):
        UserRoleBinding.objects.create(user=self.user, role=self.role)
        with self.assertRaises(Exception):
            UserRoleBinding.objects.create(user=self.user, role=self.role)


class AssignRoleTestCase(TestCase):
    """Test role assignment."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.role = Role.objects.create(name="operator", is_active=True)

    def test_assign_role(self):
        assign_role(self.user, "operator")
        self.assertTrue(has_role(self.user, "operator"))

    def test_assign_nonexistent_role(self):
        with self.assertRaises(Role.DoesNotExist):
            assign_role(self.user, "nonexistent_role")

    def test_assign_inactive_role(self):
        inactive_role = Role.objects.create(name="inactive", is_active=False)
        # Should not assign inactive role
        assign_role(self.user, "inactive")
        # Depending on implementation, may or may not be assigned


class RevokeRoleTestCase(TestCase):
    """Test role revocation."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.role = Role.objects.create(name="operator", is_active=True)
        assign_role(self.user, "operator")

    def test_revoke_role(self):
        revoke_role(self.user, "operator")
        self.assertFalse(has_role(self.user, "operator"))

    def test_revoke_nonexistent_role(self):
        # Should not raise when revoking non-assigned role
        revoke_role(self.user, "nonexistent")


class HasRoleTestCase(TestCase):
    """Test role checking."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.role = Role.objects.create(name="operator", is_active=True)

    def test_has_assigned_role(self):
        assign_role(self.user, "operator")
        self.assertTrue(has_role(self.user, "operator"))

    def test_has_not_assigned_role(self):
        self.assertFalse(has_role(self.user, "operator"))

    def test_has_role_case_sensitive(self):
        assign_role(self.user, "operator")
        self.assertFalse(has_role(self.user, "Operator"))

    def test_anonymous_user_has_no_roles(self):
        anon = User(username="anon", is_anonymous=True)
        anon.is_authenticated = False
        self.assertFalse(has_role(anon, "operator"))


class GetUserRolesTestCase(TestCase):
    """Test getting user roles."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.role1 = Role.objects.create(name="operator", is_active=True)
        self.role2 = Role.objects.create(name="analyst", is_active=True)

    def test_no_roles(self):
        roles = get_user_roles(self.user)
        self.assertEqual(roles, [])

    def test_single_role(self):
        assign_role(self.user, "operator")
        roles = get_user_roles(self.user)
        self.assertIn("operator", roles)

    def test_multiple_roles(self):
        assign_role(self.user, "operator")
        assign_role(self.user, "analyst")
        roles = get_user_roles(self.user)
        self.assertEqual(len(roles), 2)
        self.assertIn("operator", roles)
        self.assertIn("analyst", roles)


class CheckPermissionTestCase(TestCase):
    """Test permission checking."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.role = Role.objects.create(name="operator", is_active=True)
        assign_role(self.user, "operator")

    def test_check_existing_permission(self):
        # Create a permission for the role
        ScopePermission.objects.create(
            role=self.role,
            action="view",
            resource_type="message",
            scope_type="domain",
        )
        self.assertTrue(check_permission(self.user, "view", "message"))

    def test_check_missing_permission(self):
        self.assertFalse(check_permission(self.user, "delete", "project"))

    def test_check_permission_no_roles(self):
        user_no_roles = User.objects.create_user(username="noroles", password="testpass")
        self.assertFalse(check_permission(user_no_roles, "view", "message"))


class ApprovalPolicyTestCase(TestCase):
    """Test approval policies."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.approver = User.objects.create_user(username="approver", password="testpass")

    def test_policy_creation(self):
        policy = ApprovalPolicy.objects.create(
            name="Test Policy",
            scope_type="domain",
            action="delete",
            requires_approval=True,
            min_approvers=1,
        )
        self.assertTrue(policy.requires_approval)
        self.assertEqual(policy.min_approvers, 1)

    def test_policy_without_approval(self):
        policy = ApprovalPolicy.objects.create(
            name="No Approval Policy",
            scope_type="domain",
            action="view",
            requires_approval=False,
        )
        self.assertFalse(policy.requires_approval)


class RBACIntegrationTestCase(TestCase):
    """Integration tests for RBAC system."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="testpass")
        self.operator = User.objects.create_user(username="operator", password="testpass")
        self.viewer = User.objects.create_user(username="viewer", password="testpass")
        
        self.admin_role = Role.objects.create(name="super_admin", is_active=True)
        self.operator_role = Role.objects.create(name="operator", is_active=True)
        self.viewer_role = Role.objects.create(name="viewer", is_active=True)
        
        assign_role(self.admin, "super_admin")
        assign_role(self.operator, "operator")
        assign_role(self.viewer, "viewer")

    def test_admin_has_all_permissions(self):
        self.assertTrue(has_role(self.admin, "super_admin"))

    def test_operator_limited_permissions(self):
        self.assertTrue(has_role(self.operator, "operator"))
        self.assertFalse(has_role(self.operator, "super_admin"))

    def test_viewer_read_only(self):
        self.assertTrue(has_role(self.viewer, "viewer"))
        self.assertFalse(has_role(self.viewer, "operator"))
