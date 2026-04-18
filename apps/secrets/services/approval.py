"""Secret approval service — expiry checking, revocation, and audit trail for P2.1."""

import logging
from datetime import datetime, timezone
from typing import Optional

from django.utils import timezone as django_tz
from apps.secrets.models import SecretRecord, SecretAccessLog

logger = logging.getLogger(__name__)


def check_and_enforce_expiry():
    """Check all secret grants for expiry and revoke expired ones.

    Call periodically (e.g. via cron or management command).
    Returns count of revoked grants.
    """
    now = django_tz.now()
    expired = SecretAccessLog.objects.filter(
        is_deleted=False,
        access_mode="grant",
        expires_at__isnull=False,
        expires_at__lte=now,
        revoked_at__isnull=True,
    )
    count = 0
    for log in expired:
        revoke_grant(log, reason="Automatic expiry")
        count += 1
    if count:
        logger.info("Revoked %d expired secret grants", count)
    return count


def grant_access(
    secret_record: SecretRecord,
    actor_type: str,
    actor_id: Optional[int] = None,
    reason: str = "",
    duration_seconds: int = 86400,
    granted_by: Optional[int] = None,
) -> SecretAccessLog:
    """Grant time-limited access to a secret. Returns the access log entry."""
    from datetime import timedelta
    expires_at = django_tz.now() + timedelta(seconds=duration_seconds)
    log = SecretAccessLog.objects.create(
        secret_record=secret_record,
        actor_type=actor_type,
        actor_id=actor_id,
        access_mode="grant",
        reason=reason,
        expires_at=expires_at,
        granted_by_id=granted_by,
    )
    secret_record.last_accessed_at = django_tz.now()
    secret_record.save(update_fields=["last_accessed_at", "updated_at"])
    logger.info("Secret access granted: record=%d actor=%s:%s expires=%s",
                secret_record.id, actor_type, actor_id, expires_at.isoformat())
    return log


def revoke_grant(access_log: SecretAccessLog, reason: str = "") -> bool:
    """Revoke a previously granted secret access."""
    access_log.revoked_at = django_tz.now()
    access_log.revoke_reason = reason[:500]
    access_log.save(update_fields=["revoked_at", "revoke_reason", "updated_at"])
    logger.info("Secret access revoked: log=%d reason=%s", access_log.id, reason[:100])
    return True


def is_access_granted(secret_record: SecretRecord, actor_type: str, actor_id: Optional[int] = None) -> bool:
    """Check if there is an active (non-expired, non-revoked) grant for the actor."""
    now = django_tz.now()
    return SecretAccessLog.objects.filter(
        secret_record=secret_record,
        actor_type=actor_type,
        actor_id=actor_id,
        access_mode="grant",
        is_deleted=False,
        revoked_at__isnull=True,
    ).filter(
        expires_at__isnull=True
    ).filter(
        expires_at__gt=now
    ).exists() or SecretAccessLog.objects.filter(
        secret_record=secret_record,
        actor_type=actor_type,
        actor_id=actor_id,
        access_mode="grant",
        is_deleted=False,
        revoked_at__isnull=True,
        expires_at__isnull=True,
    ).exists()


def log_access(secret_record: SecretRecord, actor_type: str, actor_id: Optional[int] = None,
               access_mode: str = "read", reason: str = "") -> SecretAccessLog:
    """Log a secret access event for audit trail."""
    log = SecretAccessLog.objects.create(
        secret_record=secret_record,
        actor_type=actor_type,
        actor_id=actor_id,
        access_mode=access_mode,
        reason=reason,
    )
    secret_record.last_accessed_at = django_tz.now()
    secret_record.save(update_fields=["last_accessed_at", "updated_at"])
    return log


def get_audit_trail(secret_record: Optional[SecretRecord] = None, limit: int = 100):
    """Get audit trail for a specific secret or all secrets."""
    qs = SecretAccessLog.objects.filter(is_deleted=False).order_by("-created_at")
    if secret_record:
        qs = qs.filter(secret_record=secret_record)
    return qs[:limit]
