from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chat_events", "0003_message_embedding_vector")]

    operations = [
        migrations.AddField(
            model_name="telegramsource",
            name="archive_bias",
            field=models.DecimalField(decimal_places=2, default=0.85, max_digits=5),
        ),
        migrations.AddField(
            model_name="telegramsource",
            name="retrieval_weight",
            field=models.DecimalField(decimal_places=2, default=1.0, max_digits=5),
        ),
    ]
