import logging
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from django.core.cache import cache
from datetime import datetime

logger = logging.getLogger(__name__)


def health_check(request):
    checks = {}
    status = "ok"

    # DB
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        status = "degraded"

    # Cache (Redis)
    try:
        cache.set("_health", "1", 5)
        assert cache.get("_health") == "1"
        checks["cache"] = "ok"
    except Exception as e:
        checks["cache"] = f"error: {e}"
        status = "degraded"

    # LLM
    try:
        from apps.llm.client import get_llm_client
        llm = get_llm_client()
        checks["llm"] = "available" if llm.is_available() else "not_configured"
    except Exception as e:
        checks["llm"] = f"error: {e}"

    # Embeddings
    try:
        from apps.retrieval.embeddings import get_embedding_service
        emb = get_embedding_service()
        checks["embeddings"] = "available" if emb.is_available() else "not_configured"
    except Exception as e:
        checks["embeddings"] = f"error: {e}"

    code = 200 if status == "ok" else 503
    return JsonResponse({"status": status, "checks": checks, "timestamp": datetime.utcnow().isoformat()}, status=code)


def readiness_check(request):
    try:
        from apps.llm.client import get_llm_client
        llm = get_llm_client()
        if not llm.is_available():
            return JsonResponse({"ready": False, "reason": "LLM not configured"}, status=503)
    except Exception:
        return JsonResponse({"ready": False, "reason": "LLM check failed"}, status=503)

    return JsonResponse({"ready": True})


def llm_health(request):
    """Detailed LLM provider health status."""
    try:
        from apps.llm.client import get_llm_client
        client = get_llm_client()
        status = client.get_health_status()
        
        if not status["primary_available"] and not status["fallback_available"]:
            return JsonResponse({"status": "unavailable", "details": status}, status=503)
        
        if not status["primary_available"]:
            return JsonResponse({"status": "degraded", "details": status}, status=200)
        
        return JsonResponse({"status": "healthy", "details": status})
    except Exception as e:
        return JsonResponse({"status": "error", "reason": str(e)}, status=503)
