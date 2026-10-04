"""Drain the PostgreSQL outbox in a bounded, restart-safe worker invocation."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from sqlalchemy import select

from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import OrganizationRecord
from assetguard.modules.notifications.models import TelegramNotificationRecord
from assetguard.modules.notifications.service import enqueue_notification


@dataclass(frozen=True)
class TelegramSettings:
    bot_token: str
    chat_id: str
    organization_id: UUID
    public_url: str
    utc_offset_hours: int = 5

    @classmethod
    def from_environment(cls):
        token = os.environ.get("ASSETGUARD_TELEGRAM_BOT_TOKEN", "").strip()
        chat = os.environ.get("ASSETGUARD_TELEGRAM_CHAT_ID", "").strip()
        organization = os.environ.get("ASSETGUARD_TELEGRAM_ORGANIZATION_ID", "").strip()
        public_url = os.environ.get("ASSETGUARD_PUBLIC_URL", "").strip().rstrip("/")
        parsed = urlsplit(public_url)
        if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token) or not re.fullmatch(r"-?[0-9]+", chat):
            raise ValueError("Telegram token and numeric chat ID must be configured.")
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("ASSETGUARD_PUBLIC_URL must be a public HTTPS URL without credentials/query/fragment.")
        try:
            organization_id = UUID(organization)
        except ValueError:
            raise ValueError("ASSETGUARD_TELEGRAM_ORGANIZATION_ID must identify the authorized organization.") from None
        try:
            offset = int(os.environ.get("ASSETGUARD_NOTIFICATION_UTC_OFFSET_HOURS", "5"))
        except ValueError:
            raise ValueError("Notification UTC offset must be an integer between -12 and 14.") from None
        if not -12 <= offset <= 14:
            raise ValueError("Notification UTC offset must be an integer between -12 and 14.")
        return cls(token, chat, organization_id, public_url, offset)


class TelegramDeliveryError(Exception):
    """Only a bounded error code is exposed; never Telegram body/token/URL."""
    def __init__(self, code: str, retry_after: int = 0):
        super().__init__(code)
        self.code = code
        self.retry_after = min(max(retry_after, 0), 86400)


def message_body(payload: dict, public_url: str, utc_offset_hours: int = 5) -> dict:
    if not isinstance(payload, dict):
        raise TelegramDeliveryError("INVALID_PAYLOAD")
    route = payload.get("route", "")
    if not isinstance(route, str) or not re.fullmatch(r"#(?:incident|room)=[0-9a-fA-F-]{36}|#overview", route):
        raise TelegramDeliveryError("INVALID_ROUTE")
    severity_value = payload.get("severity")
    severity = {"HIGH": "Высокий", "MEDIUM": "Средний", "LOW": "Низкий"}.get(severity_value, "Информация") if isinstance(severity_value, str) else "Информация"
    try:
        occurred = datetime.fromisoformat(payload["occurred_at"])
        if occurred.tzinfo is None or any(not isinstance(payload[key], str) for key in ("title", "subject", "context")):
            raise ValueError("Invalid notification payload")
        occurred = occurred.astimezone(timezone(timedelta(hours=utc_offset_hours)))
    except (KeyError, TypeError, ValueError):
        raise TelegramDeliveryError("INVALID_PAYLOAD") from None
    text = "\n".join([
        f"🔔 AssetGuard · {payload['title']}", f"Объект: {payload['subject']}",
        f"Приоритет: {severity}", payload["context"],
        f"Время события: {occurred:%d.%m.%Y %H:%M} (UTC{utc_offset_hours:+d})", "Результат требует проверки ответственного.",
    ])
    label = "Открыть кабинет" if route.startswith("#room=") else "Открыть инцидент" if route.startswith("#incident=") else "Открыть AssetGuard"
    return {"text": text[:3500], "reply_markup": {"inline_keyboard": [[{"text": label, "url": public_url + "/" + route}]]},
            "link_preview_options": {"is_disabled": True}}


def send_message(settings: TelegramSettings, payload: dict) -> int:
    body = {"chat_id": settings.chat_id, **message_body(payload, settings.public_url, settings.utc_offset_hours)}
    request = Request(f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
                      data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
    except HTTPError as error:
        retry_after = 0
        if error.code == 429:
            try:
                retry_after = int(json.loads(error.read(65536)).get("parameters", {}).get("retry_after", 0))
            except (ValueError, TypeError, AttributeError):
                pass
        raise TelegramDeliveryError(f"HTTP_{error.code}", retry_after) from None
    except (URLError, TimeoutError, OSError):
        raise TelegramDeliveryError("NETWORK_ERROR") from None
    except (ValueError, TypeError):
        raise TelegramDeliveryError("INVALID_RESPONSE") from None
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise TelegramDeliveryError("NOT_ACCEPTED")
    message = result.get("result")
    if not isinstance(message, dict) or type(message.get("message_id")) is not int or message["message_id"] <= 0:
        raise TelegramDeliveryError("NO_MESSAGE_ID")
    chat = message.get("chat")
    if not isinstance(chat, dict) or str(chat.get("id")) != settings.chat_id:
        raise TelegramDeliveryError("WRONG_DESTINATION")
    return message["message_id"]


def drain_notifications(factory, settings: TelegramSettings, *, sender=send_message,
                        batch_size: int = 10, pause_seconds: float = 1.1, now: datetime | None = None) -> dict:
    """Claim rows with SKIP LOCKED; Telegram acceptance precedes SENT commit.

    A crash after acceptance and before commit can repeat a message. Telegram has
    no idempotency key, so this is at-least-once delivery rather than exactly-once.
    """
    result = {"sent": 0, "retry_scheduled": 0}
    started = time.monotonic()
    for _ in range(batch_size):
        if time.monotonic() - started > 45:
            break
        current = now or datetime.now(UTC)
        with factory() as session:
            notification = session.scalar(select(TelegramNotificationRecord).where(
                TelegramNotificationRecord.organization_id == settings.organization_id,
                TelegramNotificationRecord.status == "PENDING",
                TelegramNotificationRecord.next_attempt_at <= current,
            ).order_by(TelegramNotificationRecord.created_at, TelegramNotificationRecord.id).limit(1).with_for_update(skip_locked=True))
            if notification is None:
                break
            notification.attempts += 1
            try:
                message_id = sender(settings, notification.payload)
            except TelegramDeliveryError as error:
                notification.last_error_code = error.code
                backoff = min(3600, 30 * 2 ** min(notification.attempts - 1, 10))
                notification.next_attempt_at = current + timedelta(seconds=max(backoff, error.retry_after))
                result["retry_scheduled"] += 1
            else:
                notification.status = "SENT"
                notification.sent_at = datetime.now(UTC)
                notification.telegram_message_id = message_id
                notification.last_error_code = None
                result["sent"] += 1
            session.commit()
        if pause_seconds:
            time.sleep(pause_seconds)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Deliver queued incident notifications to the configured organization chat.")
    parser.add_argument("--enqueue-test", action="store_true", help="Add one explicit delivery-test event before draining.")
    args = parser.parse_args()
    try:
        settings = TelegramSettings.from_environment()
    except ValueError as error:
        print(str(error))
        return 2
    factory = get_session_factory()
    with factory() as session:
        if session.get(OrganizationRecord, settings.organization_id) is None:
            print("Configured notification organization does not exist.")
            return 2
        if args.enqueue_test:
            enqueue_notification(session, event_key=f"test:{uuid4()}", organization_id=settings.organization_id,
                room_id=None, title="Проверка доставки", subject="Очередь уведомлений",
                context="ТЕСТ: уведомление сохранено и отправлено фоновой задачей. Штатная работа продолжается.",
                route="#overview", severity="LOW", occurred_at=datetime.now(UTC))
            session.commit()
    result = drain_notifications(factory, settings)
    print(json.dumps(result))
    return 1 if result["retry_scheduled"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
