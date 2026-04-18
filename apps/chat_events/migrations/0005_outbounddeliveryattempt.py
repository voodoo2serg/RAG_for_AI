from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("chat_events", "0004_telegramsource_retrieval_weight_archive_bias"),
    ]

    operations = [
        migrations.CreateModel(
            name="OutboundDeliveryAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("delivery_status", models.CharField(
                    choices=[("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed"), ("rate_limited", "Rate Limited")],
                    default="pending", max_length=32)),
                ("attempt_number", models.IntegerField(default=1)),
                ("telegram_response_payload", models.JSONField(blank=True, default=dict)),
                ("last_error_code", models.CharField(blank=True, max_length=64)),
                ("retry_after", models.IntegerField(default=0)),
                ("response_message_id", models.CharField(blank=True, max_length=64)),
                ("delivery_log", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="attempts",
                    to="chat_events.outbounddeliverylog")),
            ],
            options={
                "ordering": ["attempt_number"],
                "db_table": "chat_events_outbound_delivery_attempt",
            },
        ),
    ]
