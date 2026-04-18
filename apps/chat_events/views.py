import hmac
import json
import logging
from datetime import datetime, timezone
from django.http import JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django_ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import TelegramSource, Message
from .serializers import TelegramSourceSerializer
from apps.retrieval.services import label_message_role, choose_retrieval_mode
from .services import normalize_text, route_message_to_project

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
@ratelimit(key="ip", rate="60/m", block=True)
def telegram_webhook(request: HttpRequest, source_slug: str):
    source = get_object_or_404(TelegramSource, slug=source_slug, is_active=True)
    if not source.is_inbound_enabled:
        return JsonResponse({"ok": False, "error": "source inbound disabled"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid JSON payload"}, status=400)

    secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if source.webhook_secret and not hmac.compare_digest(source.webhook_secret, secret_header):
        logger.warning("Webhook auth failed for source=%s request_id=%s", source_slug, getattr(request, "request_id", "-"))
        return JsonResponse({"ok": False, "error": "bad secret"}, status=403)

    message_data = payload.get("message", {})
    if not message_data:
        return JsonResponse({"ok": False, "error": "empty message"}, status=400)

    text = message_data.get("text", "")
    tg_mid = message_data.get("message_id")
    chat_id = message_data.get("chat", {}).get("id")
    reply_to = message_data.get("reply_to_message", {}).get("message_id") if message_data.get("reply_to_message") else None

    msg_date = message_data.get("date")
    if not msg_date:
        return JsonResponse({"ok": False, "error": "missing timestamp"}, status=400)
    timestamp = datetime.fromtimestamp(msg_date, tz=timezone.utc)

    normalized = normalize_text(text)
    role = label_message_role(normalized)
    mode = choose_retrieval_mode(role)
    project = route_message_to_project(normalized, source.default_domain, source)

    if tg_mid is None or chat_id is None:
        return JsonResponse({"ok": False, "error": "missing required fields"}, status=400)

    msg, created = Message.objects.get_or_create(
        source=source,
        telegram_chat_id=chat_id,
        telegram_message_id=tg_mid,
        defaults={
            "reply_to_message_id": reply_to,
            "sender_type": Message.SenderType.EXTERNAL,
            "raw_text": text,
            "normalized_text": normalized,
            "timestamp": timestamp,
            "domain": source.default_domain,
            "project": project,
            "message_role": role,
            "retrieval_mode_default": mode,
            "raw_payload": payload,
        },
    )

    if created:
        logger.info("Stored message id=%s source=%s request_id=%s", msg.id, source.slug, getattr(request, "request_id", "-"))
        from apps.chat_events.tasks import process_incoming_message
        process_incoming_message.delay(msg.id, agent_profile_slug=source.default_agent_profile.slug if source.default_agent_profile else None)
    else:
        logger.debug("Duplicate message source=%s tg_mid=%s", source.slug, tg_mid)

    return JsonResponse({"ok": True, "source": source.slug, "message_id": msg.id, "request_id": getattr(request, "request_id", "-")})


@api_view(["GET"])
def telegram_sources_list(request):
    """List all active Telegram sources for import widget"""
    sources = TelegramSource.objects.filter(is_active=True).order_by("display_name")
    serializer = TelegramSourceSerializer(sources, many=True)
    return Response(serializer.data)
