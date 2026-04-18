"""Management command to poll and run pending jobs from the JobQueue."""

import logging
import sys
import time

from django.core.management.base import BaseCommand
from django.utils import timezone as django_tz
from apps.jobs.models import JobQueue
from apps.jobs.services.runner import claim_next_job, heartbeat, mark_failed, run_job_safely

logger = logging.getLogger(__name__)

# Simple registry of job handlers by job_type
JOB_HANDLERS = {}


def register_handler(job_type: str):
    """Decorator to register a function as a job handler."""
    def decorator(func):
        JOB_HANDLERS[job_type] = func
        return func
    return decorator


def get_handler(job_type: str):
    """Get the handler function for a given job_type."""
    return JOB_HANDLERS.get(job_type)


class Command(BaseCommand):
    help = "Poll and run pending jobs from the queue"

    def add_arguments(self, parser):
        parser.add_argument("--job-type", type=str, default=None, help="Only run jobs of this type")
        parser.add_argument("--max-jobs", type=int, default=100, help="Max jobs to process per run")
        parser.add_argument("--loop", action="store_true", help="Run in continuous loop mode")
        parser.add_argument("--poll-interval", type=int, default=5, help="Seconds between polls in loop mode")

    def handle(self, *args, **options):
        job_type = options.get("job_type")
        max_jobs = options.get("max_jobs")
        loop_mode = options.get("loop")
        poll_interval = options.get("poll_interval")

        processed = 0
        try:
            while processed < max_jobs or loop_mode:
                job = claim_next_job(job_type=job_type)
                if not job:
                    if loop_mode:
                        self.stdout.write(f"[{django_tz.now().isoformat()}] No jobs pending, sleeping {poll_interval}s...")
                        time.sleep(poll_interval)
                        continue
                    break

                handler = get_handler(job.job_type)
                if not handler:
                    self.stderr.write(self.style.WARNING(f"No handler registered for job type: {job.job_type}"))
                    mark_failed(job, f"No handler for job type: {job.job_type}")
                    processed += 1
                    continue

                self.stdout.write(f"Running job #{job.id} ({job.job_type}) attempt={job.attempt_count}")
                run_job_safely(job, handler)
                processed += 1
                if not loop_mode:
                    self.stdout.write(self.style.SUCCESS(f"Job #{job.id} -> {job.status}"))

        except KeyboardInterrupt:
            self.stdout.write("\nInterrupted")
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} jobs"))
