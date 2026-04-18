from django.db import models
from apps.core.models import TimeStampedModel


class JobQueue(TimeStampedModel):
    """Background job queue with retry, idempotency, and dead-letter support."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"
        RETRY = "retry", "Retry"
        DEAD_LETTER = "dead_letter", "Dead Letter"
        CANCELLED = "cancelled", "Cancelled"

    job_type = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    priority = models.IntegerField(default=100, db_index=True)
    available_at = models.DateTimeField(db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_text = models.TextField(blank=True)

    # P2.1 fields — idempotency, retry, observability
    idempotency_key = models.CharField(max_length=255, blank=True, db_index=True, unique=True,
                                       help_text="Prevents duplicate execution of the same job")
    attempt_count = models.IntegerField(default=0, help_text="Current retry attempt number")
    max_attempts = models.IntegerField(default=3, help_text="Maximum retry attempts before dead-letter")
    last_heartbeat_at = models.DateTimeField(null=True, blank=True, help_text="Last alive signal from worker")
    dead_letter_reason = models.TextField(blank=True, help_text="Reason why job was moved to dead-letter")
    worker_name = models.CharField(max_length=128, blank=True, help_text="Identifier of the worker processing this job")
    trace_id = models.CharField(max_length=64, blank=True, db_index=True, help_text="Distributed tracing identifier")

    class Meta:
        db_table = "jobs_jobqueue"
        ordering = ["-priority", "available_at"]
        indexes = [
            models.Index(fields=["status", "priority", "available_at"], name="idx_jobs_queue_poll"),
            models.Index(fields=["job_type", "status"], name="idx_jobs_type_status"),
        ]

    def __str__(self):
        return f"Job #{self.id} ({self.job_type}) [{self.status}]"
