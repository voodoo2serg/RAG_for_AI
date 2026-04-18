from django.db import migrations
import apps.core.vector


class Migration(migrations.Migration):
    dependencies = [
        ('retrieval', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ragcorpusentry',
            name='embedding',
            field=apps.core.vector.EmbeddingField(blank=True, null=True),
        ),
    ]
