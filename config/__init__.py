"""Project bootstrap helpers."""

try:
    from .celery import app as celery_app  # noqa
except Exception:  # pragma: no cover - optional in local/dev bootstrap
    celery_app = None

__all__ = ("celery_app",)
