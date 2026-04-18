import logging
from typing import Optional
import requests
from django.conf import settings
from apps.secrets.broker import get_secret_broker
from apps.chat_events.models import TelegramSource, OutboundDeliveryLog

logger = logging.getLogger(__name__)


class TelegramBotClient:
    def __init__(self, source: TelegramSource):
        self.source = source

    def _get_token(self) -> Optional[str]:
        if self.source.bot_token_secret_id:
            broker = get_secret_broker()
            return broker.decrypt(self.source.bot_token_secret.encrypted_value)
        return settings.TELEGRAM_BOT_TOKEN or None

    def send_message(self, chat_id: int, text: str, reply_to_message_id: int | None = None, message=None):
        log = OutboundDeliveryLog.objects.create(
            source=self.source,
            message=message,
            target_chat_id=chat_id,
            text=text[:4000],
            status=OutboundDeliveryLog.Status.PENDING,
        )
        token = self._get_token()
        if not token:
            log.status = OutboundDeliveryLog.Status.FAILED
            log.error_text = "No bot token configured"
            log.save(update_fields=["status", "error_text", "updated_at"])
            return log
        if not self.source.is_outbound_enabled:
            log.status = OutboundDeliveryLog.Status.FAILED
            log.error_text = "Outbound disabled for source"
            log.save(update_fields=["status", "error_text", "updated_at"])
            return log
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(str(data))
            log.status = OutboundDeliveryLog.Status.SENT
            log.provider_message_id = str(data.get("result", {}).get("message_id", ""))
            log.save(update_fields=["status", "provider_message_id", "updated_at"])
        except Exception as exc:
            logger.exception("Failed to send telegram message for source=%s", self.source.slug)
            log.status = OutboundDeliveryLog.Status.FAILED
            log.error_text = str(exc)[:1000]
            log.save(update_fields=["status", "error_text", "updated_at"])
        return log


def get_telegram_client(source: TelegramSource) -> TelegramBotClient:
    return TelegramBotClient(source)
