"""Management command to requeue dead-lettered jobs for retry."""

from django.core.management.base import BaseCommand
from apps.jobs.services.retry import requeue_dead_letter_jobs


class Command(BaseCommand):
    help = "Requeue dead-lettered jobs for another round of execution"

    def add_arguments(self, parser):
        parser.add_argument("--max-count", type=int, default=50, help="Maximum jobs to requeue")

    def handle(self, *args, **options):
        count = requeue_dead_letter_jobs(max_count=options["max_count"])
        self.stdout.write(self.style.SUCCESS(f"Requeued {count} dead-letter jobs"))
