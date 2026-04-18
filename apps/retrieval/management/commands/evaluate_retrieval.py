from django.core.management.base import BaseCommand
from apps.retrieval.evaluation import evaluate_cases


class Command(BaseCommand):
    help = "Run retrieval evaluation suite"

    def add_arguments(self, parser):
        parser.add_argument("--name", default="manual")

    def handle(self, *args, **options):
        run = evaluate_cases(options["name"])
        self.stdout.write(self.style.SUCCESS(f"Run {run.id}: recall@5={run.average_recall_at_5} mrr={run.average_mrr}"))
