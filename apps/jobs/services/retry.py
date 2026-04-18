"""Retry service for failed jobs — exponential backoff and dead-letter management."""

import logging
from datetime import timedelta

from django.utils import timezone as django_tz
from apps.jobs.models import JobQueue

logger = logging.getLogger(__name__)

# Exponential backoff: 60s, 300s, 900s, 1800s, 3600s
BACKOFF_SECONDS = [60, 300, 900, 1800, 3600]


def requeue_for_retry(job: JobQueue) -> JobQueue:
    """Move a failed job back to retry queue with exponential backoff."""
    attempt = job.attempt_count or 1
    delay_idx = min(attempt - 1, len(BACKOFF_SECONDS) - 1)
    delay_seconds = BACKOFF_SECONDS[delay_idx]

    job.status = JobQueue.Status.RETRY
    job.available_at = django_tz.now() + timedelta(seconds=delay_seconds)
    job.save(update_fields=["status", "available_at", "updated_at"])
    logger.info("Job #%d requeued for retry: type=%s attempt=%d delay=%ds",
                job.id, job.job_type, attempt, delay_seconds)
    return job


def requeue_dead_letter_jobs(max_count: int = 50) -> int:
    """Requeue all dead-letter jobs for retry (admin action)."""
    jobs = JobQueue.objects.filter(
        status=JobQueue.Status.DEAD_LETTER, is_deleted=False
    ).order_by("-created_at")[:max_count]
    count = 0
    for job in jobs:
        job.status = JobQueue.Status.QUEUED
        job.attempt_count = 0
        job.error_text = ""
        job.dead_letter_reason = ""
        job.available_at = django_tz.now()
        job.save(update_fields=["status", "attempt_count", "error_text", "dead_letter_reason",
                                 "available_at", "updated_at"])
        count += 1
    logger.info("Requeued %d dead-letter jobs", count)
    return count


def cancel_stale_jobs(timeout_seconds: int = 3600) -> int:
    """Cancel jobs that have been running too long without heartbeat.

    Useful for detecting crashed workers.
    """
    cutoff = django_tz.now() - timedelta(seconds=timeout_seconds)
    count, _ = JobQueue.objects.filter(
        status=JobQueue.Status.RUNNING,
        last_heartbeat_at__lt=cutoff,
        is_deleted=False,
    ).update(status=JobQueue.Status.CANCELLED, finished_at=django_tz.now())
    if count:
        logger.warning("Cancelled %d stale jobs (no heartbeat for %ds)", count, timeout_seconds)
    return count
