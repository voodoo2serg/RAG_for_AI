from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("wiki", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="wikipage",
            name="current_revision",
            field=models.ForeignKey(
                blank=True,
                help_text="The currently active revision for this wiki page",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="current_for_page",
                to="wiki.wikirevision",
            ),
        ),
    ]
