import logging
import time
from typing import Optional
import requests
from django.conf import settings
from apps.secrets.broker import get_secret_broker
from apps.chat_events.models import TelegramSource, OutboundDeliveryLog, OutboundDeliveryAttempt

logger = logging.getLogger(__name__)

MAX_DELIVERY_ATTEMPTS = 3
INITIAL_RETRY_DELAY = 5  # seconds


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
        return self._deliver_with_retry(log, chat_id, text, reply_to_message_id)

    def _deliver_with_retry(self, log: OutboundDeliveryLog, chat_id: int, text: str, reply_to_message_id: int | None = None):
        """Attempt delivery with automatic retry on transient failures."""
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

        attempt_number = 0
        for attempt in range(MAX_DELIVERY_ATTEMPTS):
            attempt_number = attempt + 1
            attempt_record = self._create_attempt(log, attempt_number)
            result = self._single_send(log, attempt_record, token, chat_id, text, reply_to_message_id)

            if result == "sent":
                return log
            elif result == "rate_limited":
                # Wait for Telegram's retry_after, then retry
                retry_delay = attempt_record.retry_after or (INITIAL_RETRY_DELAY * (2 ** attempt))
                logger.info("Rate limited, waiting %ds before retry (source=%s)", retry_delay, self.source.slug)
                time.sleep(min(retry_delay, 120))
                continue
            elif result == "failed_permanent":
                return log
            # Transient failure — retry after backoff
            time.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))

        # All attempts exhausted
        log.status = OutboundDeliveryLog.Status.FAILED
        log.error_text = f"All {MAX_DELIVERY_ATTEMPTS} attempts failed"
        log.save(update_fields=["status", "error_text", "updated_at"])
        return log

    def _single_send(self, log, attempt, token, chat_id, text, reply_to_message_id):
        """Execute a single send attempt and return status string."""
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()

            # Record response in attempt
            attempt.telegram_response_payload = {
                "status_code": resp.status_code,
                "ok": data.get("ok"),
                "error_code": data.get("error_code"),
                "description": data.get("description", "")[:500],
            }

            if resp.status_code == 429:
                # Rate limited
                attempt.delivery_status = OutboundDeliveryAttempt.DeliveryStatus.RATE_LIMITED
                attempt.last_error_code = "429"
                attempt.retry_after = int(data.get("parameters", {}).get("retry_after", 30))
                attempt.save(update_fields=["delivery_status", "telegram_response_payload",
                                            "last_error_code", "retry_after", "updated_at"])
                return "rate_limited"

            resp.raise_for_status()

            if not data.get("ok"):
                error_code = data.get("error_code", "unknown")
                error_desc = data.get("description", "Unknown error")
                attempt.delivery_status = OutboundDeliveryAttempt.DeliveryStatus.FAILED
                attempt.last_error_code = str(error_code)
                attempt.save(update_fields=["delivery_status", "telegram_response_payload",
                                            "last_error_code", "updated_at"])
                logger.warning("Telegram API error: %s %s (source=%s)", error_code, error_desc, self.source.slug)

                # Permanent errors: 403 Forbidden, 400 Bad Request
                if error_code in (403, 400):
                    log.status = OutboundDeliveryLog.Status.FAILED
                    log.error_text = f"Permanent error: {error_code} {error_desc}"
                    log.save(update_fields=["status", "error_text", "updated_at"])
                    return "failed_permanent"
                return "transient"

            # Success
            attempt.delivery_status = OutboundDeliveryAttempt.DeliveryStatus.SENT
            attempt.response_message_id = str(data.get("result", {}).get("message_id", ""))
            attempt.save(update_fields=["delivery_status", "telegram_response_payload",
                                        "response_message_id", "updated_at"])
            log.status = OutboundDeliveryLog.Status.SENT
            log.provider_message_id = attempt.response_message_id
            log.save(update_fields=["status", "provider_message_id", "updated_at"])
            return "sent"

        except requests.exceptions.Timeout:
            attempt.delivery_status = OutboundDeliveryAttempt.DeliveryStatus.FAILED
            attempt.last_error_code = "timeout"
            attempt.telegram_response_payload = {"error": "Request timeout"}
            attempt.save(update_fields=["delivery_status", "telegram_response_payload",
                                        "last_error_code", "updated_at"])
            return "transient"
        except requests.exceptions.ConnectionError:
            attempt.delivery_status = OutboundDeliveryAttempt.DeliveryStatus.FAILED
            attempt.last_error_code = "connection_error"
            attempt.telegram_response_payload = {"error": "Connection failed"}
            attempt.save(update_fields=["delivery_status", "telegram_response_payload",
                                        "last_error_code", "updated_at"])
            return "transient"
        except Exception as exc:
            logger.exception("Failed to send telegram message for source=%s", self.source.slug)
            attempt.delivery_status = OutboundDeliveryAttempt.DeliveryStatus.FAILED
            attempt.last_error_code = "exception"
            attempt.telegram_response_payload = {"error": str(exc)[:500]}
            attempt.save(update_fields=["delivery_status", "telegram_response_payload",
                                        "last_error_code", "updated_at"])
            log.status = OutboundDeliveryLog.Status.FAILED
            log.error_text = str(exc)[:1000]
            log.save(update_fields=["status", "error_text", "updated_at"])
            return "failed_permanent"

    def _create_attempt(self, log: OutboundDeliveryLog, attempt_number: int) -> OutboundDeliveryAttempt:
        return OutboundDeliveryAttempt.objects.create(
            delivery_log=log,
            attempt_number=attempt_number,
            delivery_status=OutboundDeliveryAttempt.DeliveryStatus.PENDING,
        )


def get_telegram_client(source: TelegramSource) -> TelegramBotClient:
    return TelegramBotClient(source)
