
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.retrieval.models import RagCorpusEntry

class Command(BaseCommand):
    help = "Mark corpus entries as hot/cold and derive duplicate group keys."

    def handle(self, *args, **kwargs):
        count = 0
        for entry in RagCorpusEntry.objects.all().iterator():
            text = (entry.text or "").strip().lower()
            if entry.entry_type in {"rule", "knowledge", "wiki"} or float(entry.retrieval_weight or 1) >= 1.1:
                entry.storage_tier = "hot"
            else:
                entry.storage_tier = "cold"
            entry.duplicate_group_key = (text[:120] if text else "")[:120]
            entry.last_indexed_at = timezone.now()
            entry.save(update_fields=["storage_tier", "duplicate_group_key", "last_indexed_at", "updated_at"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Compacted {count} corpus entries"))
