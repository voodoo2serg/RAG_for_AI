from django.db import migrations
import apps.core.vector


class Migration(migrations.Migration):
    dependencies = [
        ('chat_events', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='embedding',
            field=apps.core.vector.EmbeddingField(blank=True, help_text='Dense embedding for semantic retrieval', null=True),
        ),
    ]
