from django.core.management.base import BaseCommand
from apps.retrieval.services import rebuild_rag_corpus


class Command(BaseCommand):
    help = "Rebuild RAG corpus entries from messages, summaries, knowledge items and wiki pages"

    def handle(self, *args, **kwargs):
        count = rebuild_rag_corpus()
        self.stdout.write(self.style.SUCCESS(f"Rebuilt {count} corpus entries"))
