from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("retrieval", "0002_ragcorpusentry_embedding_vector"), ("domains_projects", "0001_initial"), ("chat_events", "0004_telegramsource_retrieval_weight_archive_bias")]

    operations = [
        migrations.AddField(
            model_name="ragcorpusentry",
            name="source_weight",
            field=models.DecimalField(decimal_places=2, default=1.0, max_digits=5),
        ),
        migrations.AddField(
            model_name="ragcorpusentry",
            name="retrieval_weight",
            field=models.DecimalField(decimal_places=2, default=1.0, max_digits=5),
        ),
        migrations.AddField(
            model_name="retrievalsession",
            name="diagnostics_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name="RetrievalEvaluationCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=255)),
                ("query_text", models.TextField()),
                ("retrieval_mode", models.CharField(choices=[("business_mode", "Business"), ("debug_mode", "Debug"), ("ops_mode", "Ops"), ("historical_mode", "Historical")], default="business_mode", max_length=64)),
                ("expected_corpus_entry_ids", models.JSONField(blank=True, default=list)),
                ("notes", models.TextField(blank=True)),
                ("domain", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="retrieval_eval_cases", to="domains_projects.domain")),
                ("project", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="retrieval_eval_cases", to="domains_projects.project")),
                ("source", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="retrieval_eval_cases", to="chat_events.telegramsource")),
            ],
        ),
        migrations.CreateModel(
            name="RetrievalEvaluationRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=255)),
                ("query_count", models.PositiveIntegerField(default=0)),
                ("average_recall_at_5", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("average_mrr", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("summary", models.JSONField(blank=True, default=dict)),
            ],
        ),
        migrations.CreateModel(
            name="RetrievalEvaluationResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("retrieved_entry_ids", models.JSONField(blank=True, default=list)),
                ("recall_at_5", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("mrr", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("diagnostics", models.JSONField(blank=True, default=dict)),
                ("case", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="retrieval.retrievalevaluationcase")),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="retrieval.retrievalevaluationrun")),
            ],
            options={"unique_together": {("run", "case")}},
        ),
        migrations.AddIndex(
            model_name="ragcorpusentry",
            index=models.Index(fields=["trust_score", "freshness_score"], name="retrieval_r_trust__2a68c8_idx"),
        ),
        migrations.AddIndex(
            model_name="ragcorpusentry",
            index=models.Index(fields=["source_weight", "retrieval_weight"], name="retrieval_r_source__53fb66_idx"),
        ),
    ]
