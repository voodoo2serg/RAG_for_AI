"""Job migration to add P2.1 fields."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobqueue",
            name="idempotency_key",
            field=models.CharField(blank=True, db_index=True, max_length=255, unique=True),
        ),
        migrations.AddField(
            model_name="jobqueue",
            name="attempt_count",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="jobqueue",
            name="max_attempts",
            field=models.IntegerField(default=3),
        ),
        migrations.AddField(
            model_name="jobqueue",
            name="last_heartbeat_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobqueue",
            name="dead_letter_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="jobqueue",
            name="worker_name",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="jobqueue",
            name="trace_id",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AlterField(
            model_name="jobqueue",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("done", "Done"),
                    ("failed", "Failed"),
                    ("retry", "Retry"),
                    ("dead_letter", "Dead Letter"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                max_length=16,
            ),
        ),
    ]
