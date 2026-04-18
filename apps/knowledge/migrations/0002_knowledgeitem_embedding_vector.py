from django.db import migrations
import apps.core.vector


class Migration(migrations.Migration):
    dependencies = [
        ('knowledge', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='knowledgeitem',
            name='embedding',
            field=apps.core.vector.EmbeddingField(blank=True, help_text='Dense embedding for semantic retrieval', null=True),
        ),
    ]
