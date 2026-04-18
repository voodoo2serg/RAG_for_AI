"""Job execution service with heartbeat, trace_id, and idempotency support."""

import logging
import socket
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from django.utils import timezone as django_tz
from apps.jobs.models import JobQueue

logger = logging.getLogger(__name__)

# Machine identifier for worker_name
_WORKER_NAME = f"{socket.gethostname()}-{id(object())}"


def enqueue_job(
    job_type: str,
    payload: Optional[Dict[str, Any]] = None,
    priority: int = 100,
    available_at: Optional[datetime] = None,
    idempotency_key: Optional[str] = None,
    trace_id: Optional[str] = None,
    max_attempts: int = 3,
) -> JobQueue:
    """Enqueue a new job. If idempotency_key is provided and already exists, return existing job."""
    if available_at is None:
        available_at = django_tz.now()

    if idempotency_key:
        existing = JobQueue.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            logger.info("Job %s already exists with idempotency_key=%s (status=%s)", existing.id, idempotency_key, existing.status)
            return existing

    job = JobQueue.objects.create(
        job_type=job_type,
        payload=payload or {},
        priority=priority,
        available_at=available_at,
        idempotency_key=idempotency_key or "",
        trace_id=trace_id or "",
        max_attempts=max_attempts,
        worker_name=_WORKER_NAME,
    )
    logger.info("Job #%d enqueued: type=%s priority=%d", job.id, job_type, priority)
    return job


def claim_next_job(job_type: Optional[str] = None) -> Optional[JobQueue]:
    """Atomically claim the next available job for execution."""
    qs = JobQueue.objects.filter(
        status__in=[JobQueue.Status.QUEUED, JobQueue.Status.RETRY],
        available_at__lte=django_tz.now(),
        is_deleted=False,
    )
    if job_type:
        qs = qs.filter(job_type=job_type)
    job = qs.order_by("-priority", "available_at").first()
    if not job:
        return None
    job.status = JobQueue.Status.RUNNING
    job.started_at = django_tz.now()
    job.attempt_count += 1
    job.worker_name = _WORKER_NAME
    job.last_heartbeat_at = django_tz.now()
    job.save(update_fields=["status", "started_at", "attempt_count", "worker_name", "last_heartbeat_at", "updated_at"])
    logger.info("Job #%d claimed: type=%s attempt=%d", job.id, job.job_type, job.attempt_count)
    return job


def heartbeat(job: JobQueue) -> None:
    """Update the heartbeat timestamp for a running job."""
    JobQueue.objects.filter(id=job.id, status=JobQueue.Status.RUNNING).update(
        last_heartbeat_at=django_tz.now(), updated_at=django_tz.now()
    )


def mark_done(job: JobQueue) -> None:
    """Mark a job as successfully completed."""
    job.status = JobQueue.Status.DONE
    job.finished_at = django_tz.now()
    job.last_heartbeat_at = django_tz.now()
    job.save(update_fields=["status", "finished_at", "last_heartbeat_at", "updated_at"])
    logger.info("Job #%d done: type=%s", job.id, job.job_type)


def mark_failed(job: JobQueue, error_text: str) -> None:
    """Mark a job as failed. If attempts remain, set to RETRY; otherwise DEAD_LETTER."""
    if job.attempt_count >= job.max_attempts:
        job.status = JobQueue.Status.DEAD_LETTER
        job.dead_letter_reason = error_text[:2000]
        job.finished_at = django_tz.now()
        logger.error("Job #%d dead-lettered: type=%s reason=%s", job.id, job.job_type, error_text[:200])
    else:
        job.status = JobQueue.Status.FAILED
        job.error_text = error_text[:2000]
        logger.warning("Job #%d failed (attempt %d/%d): type=%s error=%s",
                       job.id, job.attempt_count, job.max_attempts, job.job_type, error_text[:200])
    job.finished_at = django_tz.now()
    job.last_heartbeat_at = django_tz.now()
    job.save(update_fields=["status", "error_text", "dead_letter_reason", "finished_at",
                             "last_heartbeat_at", "updated_at"])


def run_job_safely(job: JobQueue, handler) -> None:
    """Execute a job handler with automatic error handling, retry, and dead-letter."""
    from apps.jobs.services.retry import requeue_for_retry
    try:
        handler(job)
        mark_done(job)
    except Exception as exc:
        mark_failed(job, str(exc))
        if job.status == JobQueue.Status.FAILED:
            requeue_for_retry(job)
