from __future__ import annotations

from django.conf import settings
from django.db import models


def is_postgres_vector_enabled() -> bool:
    engine = settings.DATABASES["default"]["ENGINE"]
    return "postgresql" in engine and getattr(settings, "ENABLE_PGVECTOR", True)


if is_postgres_vector_enabled():
    try:
        from pgvector.django import VectorField as BaseVectorField  # type: ignore
    except ImportError:  # pragma: no cover
        BaseVectorField = None
else:
    BaseVectorField = None


if BaseVectorField is not None:
    class EmbeddingField(BaseVectorField):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("dimensions", getattr(settings, "EMBEDDING_DIMENSION", 1536))
            super().__init__(*args, **kwargs)
else:
    class EmbeddingField(models.JSONField):
        """Fallback field for sqlite/dev environments.

        In P1.1 the canonical production path is PostgreSQL + pgvector.
        This field keeps dev/test scaffolds usable when pgvector is unavailable.
        """

        def __init__(self, *args, **kwargs):
            kwargs.setdefault("default", list)
            kwargs.setdefault("blank", True)
            kwargs.setdefault("null", True)
            super().__init__(*args, **kwargs)
