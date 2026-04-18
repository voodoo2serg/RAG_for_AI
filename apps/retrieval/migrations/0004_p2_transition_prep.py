
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("retrieval", "0003_p1_2_retrieval_quality_hardening" if True else "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ragcorpusentry",
            name="storage_tier",
            field=models.CharField(default="hot", max_length=16),
        ),
        migrations.AddField(
            model_name="ragcorpusentry",
            name="redaction_status",
            field=models.CharField(default="clean", max_length=16),
        ),
        migrations.AddField(
            model_name="ragcorpusentry",
            name="duplicate_group_key",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="ragcorpusentry",
            name="last_indexed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ragcorpusentry",
            name="is_reviewed",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="RetrievalFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("rating", models.SmallIntegerField(default=0)),
                ("note", models.TextField(blank=True)),
                ("reviewer", models.CharField(blank=True, max_length=128)),
                ("session", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="feedback", to="retrieval.retrievalsession")),
            ],
            options={},
        ),
        migrations.CreateModel(
            name="ReviewQueueItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("queue_type", models.CharField(choices=[("project_merge","Project Merge"),("thread_review","Thread Review"),("message_relabel","Message Relabel"),("knowledge_promotion","Knowledge Promotion"),("wiki_draft","Wiki Draft"),("retrieval_outlier","Retrieval Outlier")], max_length=32)),
                ("status", models.CharField(choices=[("open","Open"),("accepted","Accepted"),("rejected","Rejected"),("applied","Applied")], default="open", max_length=16)),
                ("title", models.CharField(max_length=255)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("priority", models.IntegerField(default=100)),
                ("domain", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="review_queue_items", to="domains_projects.domain")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="review_queue_items", to="domains_projects.project")),
                ("source", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="review_queue_items", to="chat_events.telegramsource")),
            ],
            options={"ordering": ["priority", "-created_at"]},
        ),
    ]
