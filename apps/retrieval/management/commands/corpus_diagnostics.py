import json
from django.core.management.base import BaseCommand
from apps.retrieval.diagnostics import build_corpus_diagnostics


class Command(BaseCommand):
    help = "Inspect retrieval diagnostics for a query"

    def add_arguments(self, parser):
        parser.add_argument("query")
        parser.add_argument("--project-id", type=int)
        parser.add_argument("--domain-id", type=int)
        parser.add_argument("--source-id", type=int)
        parser.add_argument("--mode", default="business_mode")

    def handle(self, *args, **options):
        payload = build_corpus_diagnostics(
            query=options["query"],
            project_id=options.get("project_id"),
            domain_id=options.get("domain_id"),
            source_id=options.get("source_id"),
            retrieval_mode=options["mode"],
        )
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
