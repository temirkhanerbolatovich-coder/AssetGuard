"""Enqueue bounded, non-secret incident context without performing network IO."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from assetguard.modules.notifications.models import TelegramNotificationRecord


def _bounded_line(value: str) -> str:
    return " ".join(str(value).split())[:400]


def enqueue_notification(session: Session, *, event_key: str, organization_id: UUID | None,
                         room_id: UUID | None, title: str, subject: str, context: str,
                         route: str, severity: str, occurred_at: datetime) -> UUID | None:
    """Persist at most one outbox row per event in the caller's transaction."""
    notification_id = uuid4()
    return session.scalar(insert(TelegramNotificationRecord).values(
        id=notification_id, event_key=event_key, organization_id=organization_id, room_id=room_id,
        payload={"title": _bounded_line(title), "subject": _bounded_line(subject), "context": _bounded_line(context),
                 "route": route, "severity": severity, "occurred_at": occurred_at.isoformat()},
        status="PENDING", attempts=0, created_at=datetime.now(UTC), next_attempt_at=datetime.now(UTC),
    ).on_conflict_do_nothing(index_elements=["event_key"]).returning(TelegramNotificationRecord.id))
