
from django.core.management.base import BaseCommand, CommandError
from apps.chat_events.models import TelegramSource
from apps.retrieval.models import RetrievalEvaluationCase

class Command(BaseCommand):
    help = "Bootstrap retrieval evaluation cases for a specific source."

    def add_arguments(self, parser):
        parser.add_argument("source_slug")
        parser.add_argument("--queries", nargs="*", default=["overview", "latest decisions", "debug issues"])

    def handle(self, *args, **kwargs):
        try:
            source = TelegramSource.objects.get(slug=kwargs["source_slug"])
        except TelegramSource.DoesNotExist as exc:
            raise CommandError(f"Unknown source: {kwargs['source_slug']}") from exc
        created = 0
        for query in kwargs["queries"]:
            RetrievalEvaluationCase.objects.get_or_create(
                source=source,
                name=f"{source.slug}:{query}",
                defaults={"query_text": query, "retrieval_mode": source.default_retrieval_mode},
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Prepared {created} source evaluation cases"))
