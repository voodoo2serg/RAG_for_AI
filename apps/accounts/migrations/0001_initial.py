from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=64, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"abstract": False, "db_table": "accounts_role"},
        ),
        migrations.CreateModel(
            name="UserRoleBinding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("granted_at", models.DateTimeField(auto_now_add=True)),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_bindings", to="accounts.role")),
                ("granted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="granted_bindings", to="auth.user")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_bindings", to="auth.user")),
            ],
            options={"abstract": False, "db_table": "accounts_user_role_binding", "unique_together": {("user", "role")}},
        ),
        migrations.CreateModel(
            name="ScopePermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("scope_type", models.CharField(default="global", max_length=32)),
                ("action", models.CharField(help_text="e.g. view, edit, delete, approve, manage", max_length=64)),
                ("resource_type", models.CharField(help_text="e.g. message, wiki, secret, job, source", max_length=64)),
                ("resource_id", models.BigIntegerField(blank=True, help_text="Optional specific resource id", null=True)),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="permissions", to="accounts.role")),
            ],
            options={"abstract": False, "db_table": "accounts_scope_permission", "unique_together": {("role", "scope_type", "action", "resource_type")}},
        ),
        migrations.CreateModel(
            name="ApprovalPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("scope_type", models.CharField(default="global", max_length=32)),
                ("resource_type", models.CharField(default="*", max_length=64)),
                ("auto_approve", models.BooleanField(default=False)),
                ("max_duration_seconds", models.IntegerField(default=86400, help_text="Max grant duration in seconds (default 24h)")),
                ("description", models.TextField(blank=True)),
                ("required_role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_policies", to="accounts.role")),
            ],
            options={"abstract": False, "db_table": "accounts_approval_policy", "unique_together": {("scope_type", "resource_type")}},
        ),
    ]
