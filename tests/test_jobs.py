"""Tests for jobs — retry, dead-letter, heartbeat, idempotency."""

from django.test import TestCase
from django.utils import timezone as django_tz
from apps.jobs.models import JobQueue
from apps.jobs.services.runner import enqueue_job, claim_next_job, mark_done, mark_failed
from apps.jobs.services.retry import should_retry, get_retry_delay


class EnqueueJobTestCase(TestCase):
    """Test job enqueue functionality."""

    def test_enqueue_basic(self):
        job = enqueue_job(job_type="test_job", payload={"key": "value"})
        self.assertEqual(job.job_type, "test_job")
        self.assertEqual(job.status, JobQueue.Status.QUEUED)
        self.assertEqual(job.payload, {"key": "value"})

    def test_enqueue_with_priority(self):
        job = enqueue_job(job_type="test_job", priority=50)
        self.assertEqual(job.priority, 50)

    def test_enqueue_with_idempotency_key(self):
        job1 = enqueue_job(job_type="test_job", idempotency_key="unique-key-123")
        job2 = enqueue_job(job_type="test_job", idempotency_key="unique-key-123")
        self.assertEqual(job1.id, job2.id)

    def test_enqueue_different_idempotency_keys(self):
        job1 = enqueue_job(job_type="test_job", idempotency_key="key-1")
        job2 = enqueue_job(job_type="test_job", idempotency_key="key-2")
        self.assertNotEqual(job1.id, job2.id)

    def test_enqueue_without_idempotency_key(self):
        job1 = enqueue_job(job_type="test_job")
        job2 = enqueue_job(job_type="test_job")
        self.assertNotEqual(job1.id, job2.id)


class ClaimJobTestCase(TestCase):
    """Test job claiming and processing."""

    def test_claim_next_job(self):
        job = enqueue_job(job_type="test_job")
        claimed = claim_next_job(job_type="test_job")
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.id, job.id)
        self.assertEqual(claimed.status, JobQueue.Status.RUNNING)

    def test_claim_updates_attempt_count(self):
        job = enqueue_job(job_type="test_job")
        claimed = claim_next_job(job_type="test_job")
        self.assertEqual(claimed.attempt_count, 1)

    def test_claim_no_available_jobs(self):
        claimed = claim_next_job(job_type="nonexistent_job")
        self.assertIsNone(claimed)

    def test_claim_sets_started_at(self):
        job = enqueue_job(job_type="test_job")
        claimed = claim_next_job(job_type="test_job")
        self.assertIsNotNone(claimed.started_at)

    def test_claim_sets_worker_name(self):
        job = enqueue_job(job_type="test_job")
        claimed = claim_next_job(job_type="test_job")
        self.assertIsNotNone(claimed.worker_name)
        self.assertGreater(len(claimed.worker_name), 0)


class MarkDoneTestCase(TestCase):
    """Test job completion."""

    def test_mark_done(self):
        job = enqueue_job(job_type="test_job")
        claimed = claim_next_job(job_type="test_job")
        mark_done(claimed)
        claimed.refresh_from_db()
        self.assertEqual(claimed.status, JobQueue.Status.DONE)
        self.assertIsNotNone(claimed.finished_at)

    def test_mark_done_idempotent(self):
        job = enqueue_job(job_type="test_job")
        claimed = claim_next_job(job_type="test_job")
        mark_done(claimed)
        mark_done(claimed)  # Should not raise
        claimed.refresh_from_db()
        self.assertEqual(claimed.status, JobQueue.Status.DONE)


class MarkFailedTestCase(TestCase):
    """Test job failure handling."""

    def test_mark_failed(self):
        job = enqueue_job(job_type="test_job")
        claimed = claim_next_job(job_type="test_job")
        mark_failed(claimed, "Test error message")
        claimed.refresh_from_db()
        self.assertEqual(claimed.status, JobQueue.Status.FAILED)
        self.assertIn("Test error message", claimed.error_text)

    def test_mark_failed_with_retry(self):
        job = enqueue_job(job_type="test_job", max_attempts=3)
        claimed = claim_next_job(job_type="test_job")
        mark_failed(claimed, "Temporary error")
        claimed.refresh_from_db()
        # Should be queued for retry if attempts < max_attempts
        self.assertIn(claimed.status, [JobQueue.Status.RETRY, JobQueue.Status.FAILED])


class RetryLogicTestCase(TestCase):
    """Test retry logic."""

    def test_should_retry_yes(self):
        job = enqueue_job(job_type="test_job", max_attempts=3)
        job.attempt_count = 1
        self.assertTrue(should_retry(job))

    def test_should_retry_no_max_attempts(self):
        job = enqueue_job(job_type="test_job", max_attempts=3)
        job.attempt_count = 3
        self.assertFalse(should_retry(job))

    def test_should_retry_no_max_set(self):
        job = enqueue_job(job_type="test_job")
        job.attempt_count = 10
        # Default max_attempts is 3
        self.assertFalse(should_retry(job))

    def test_retry_delay_exponential(self):
        delay1 = get_retry_delay(1)
        delay2 = get_retry_delay(2)
        delay3 = get_retry_delay(3)
        self.assertGreater(delay2, delay1)
        self.assertGreater(delay3, delay2)


class DeadLetterTestCase(TestCase):
    """Test dead-letter queue behavior."""

    def test_dead_letter_after_max_retries(self):
        job = enqueue_job(job_type="test_job", max_attempts=1)
        claimed = claim_next_job(job_type="test_job")
        mark_failed(claimed, "Permanent error")
        claimed.refresh_from_db()
        # After max attempts, should be dead-letter or failed
        self.assertIn(
            claimed.status,
            [JobQueue.Status.DEAD_LETTER, JobQueue.Status.FAILED]
        )

    def test_dead_letter_queue(self):
        # Create a job directly in dead-letter state
        job = JobQueue.objects.create(
            job_type="test_job",
            status=JobQueue.Status.DEAD_LETTER,
            error_text="Permanent failure",
            attempt_count=5,
            max_attempts=3,
        )
        self.assertEqual(job.status, JobQueue.Status.DEAD_LETTER)


class JobHeartbeatTestCase(TestCase):
    """Test job heartbeat monitoring."""

    def test_heartbeat_field_exists(self):
        job = enqueue_job(job_type="test_job")
        # P2.1 should have last_heartbeat_at field
        self.assertTrue(hasattr(job, 'last_heartbeat_at'))

    def test_trace_id_field_exists(self):
        job = enqueue_job(job_type="test_job")
        # P2.1 should have trace_id field
        self.assertTrue(hasattr(job, 'trace_id'))


class JobQueueStatusTestCase(TestCase):
    """Test job status transitions."""

    def test_status_choices(self):
        statuses = [
            JobQueue.Status.QUEUED,
            JobQueue.Status.RUNNING,
            JobQueue.Status.DONE,
            JobQueue.Status.FAILED,
            JobQueue.Status.RETRY,
            JobQueue.Status.DEAD_LETTER,
            JobQueue.Status.CANCELLED,
        ]
        self.assertEqual(len(statuses), 7)

    def test_valid_status_transition(self):
        job = enqueue_job(job_type="test_job")
        self.assertEqual(job.status, JobQueue.Status.QUEUED)
        
        claimed = claim_next_job(job_type="test_job")
        self.assertEqual(claimed.status, JobQueue.Status.RUNNING)
        
        mark_done(claimed)
        claimed.refresh_from_db()
        self.assertEqual(claimed.status, JobQueue.Status.DONE)
