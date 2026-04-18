from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("secrets", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="secretaccesslog",
            name="access_mode",
            field=models.CharField(default="read", max_length=32),
        ),
        migrations.AddField(
            model_name="secretaccesslog",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True, help_text="Grant expiry time"),
        ),
        migrations.AddField(
            model_name="secretaccesslog",
            name="granted_by_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="secretaccesslog",
            name="revoke_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="secretaccesslog",
            name="revoked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
