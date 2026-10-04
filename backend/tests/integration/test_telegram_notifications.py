"""Durable delivery boundaries, restart/retry behavior and organization isolation."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from assetguard.infrastructure.database import get_session_factory
from assetguard.interfaces.http.health import operations_status
from assetguard.modules.assets.models import OrganizationRecord
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.notifications.delivery import TelegramDeliveryError, TelegramSettings, drain_notifications
from assetguard.modules.notifications.models import TelegramNotificationRecord
from assetguard.modules.notifications.service import enqueue_notification


def setup_queue():
    factory = get_session_factory()
    now = datetime.now(UTC)
    with factory() as session:
        organization = OrganizationRecord(name="Notification test", created_at=now)
        session.add(organization)
        session.commit()
    settings = TelegramSettings("123:test-only-placeholder", "-123", organization.id, "https://example.invalid")
    return factory, settings, now


def enqueue(session, organization_id, now, key="test-event"):
    return enqueue_notification(session, event_key=key, organization_id=organization_id,
        room_id=None, title="Test", subject="Computer", context="Check evidence", route=f"#incident={uuid4()}",
        severity="HIGH", occurred_at=now)


def test_enqueue_is_transactional_and_unique():
    factory, settings, now = setup_queue()
    with factory() as session:
        enqueue(session, settings.organization_id, now)
        session.rollback()
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(TelegramNotificationRecord)) == 0
        first = enqueue(session, settings.organization_id, now)
        assert enqueue(session, settings.organization_id, now) is None
        session.commit()
        assert session.scalar(select(func.count()).select_from(TelegramNotificationRecord)) == 1
        assert session.get(TelegramNotificationRecord, first).status == "PENDING"


def test_refusal_retries_after_restart_and_sent_event_is_not_repeated():
    factory, settings, now = setup_queue()
    with factory() as session:
        notification_id = enqueue(session, settings.organization_id, now)
        session.commit()
    def refusal(settings, payload):
        raise TelegramDeliveryError("HTTP_429", retry_after=120)
    first = drain_notifications(factory, settings, sender=refusal, pause_seconds=0, now=now + timedelta(seconds=1))
    assert first == {"sent": 0, "retry_scheduled": 1}
    with factory() as session:
        row = session.get(TelegramNotificationRecord, notification_id)
        assert row.status == "PENDING" and row.attempts == 1
        assert row.next_attempt_at >= now + timedelta(seconds=121)
        assert row.last_error_code == "HTTP_429"
        principal = AuthPrincipal(user_id=None, username="admin", role="ADMIN", session_id=None, organization_id=settings.organization_id)
        assert operations_status(session, principal)["notifications"] == {"pending": 1, "retrying": 1}
    calls = []
    def accepted(settings, payload):
        calls.append(payload)
        return 456
    assert drain_notifications(get_session_factory(), settings, sender=accepted, pause_seconds=0, now=now + timedelta(seconds=30))["sent"] == 0
    assert drain_notifications(get_session_factory(), settings, sender=accepted, pause_seconds=0, now=now + timedelta(seconds=122))["sent"] == 1
    assert drain_notifications(factory, settings, sender=accepted, pause_seconds=0, now=now + timedelta(hours=1))["sent"] == 0
    assert len(calls) == 1
    with factory() as session:
        row = session.get(TelegramNotificationRecord, notification_id)
        assert row.status == "SENT" and row.telegram_message_id == 456 and row.attempts == 2
        assert row.sent_at is not None and row.last_error_code is None


def test_foreign_and_unassigned_organizations_are_not_sent_or_counted():
    factory, settings, now = setup_queue()
    with factory() as session:
        foreign = OrganizationRecord(name="Foreign", created_at=now)
        session.add(foreign)
        session.flush()
        own_id = enqueue(session, settings.organization_id, now, "own")
        foreign_id = enqueue(session, foreign.id, now, "foreign")
        unassigned_id = enqueue(session, None, now, "unassigned")
        session.commit()
        principal = AuthPrincipal(user_id=None, username="admin", role="ADMIN", session_id=None, organization_id=settings.organization_id)
        assert operations_status(session, principal)["notifications"]["pending"] == 1
    result = drain_notifications(factory, settings, sender=lambda settings, payload: 999, pause_seconds=0, now=now + timedelta(seconds=1))
    assert result["sent"] == 1
    with factory() as session:
        assert session.get(TelegramNotificationRecord, own_id).status == "SENT"
        assert session.get(TelegramNotificationRecord, foreign_id).status == "PENDING"
        assert session.get(TelegramNotificationRecord, unassigned_id).attempts == 0


def test_parallel_worker_skips_a_claimed_notification():
    factory, settings, now = setup_queue()
    with factory() as session:
        first = enqueue(session, settings.organization_id, now, "first")
        second = enqueue(session, settings.organization_id, now, "second")
        session.commit()
    with factory() as claimant:
        claimant.scalar(select(TelegramNotificationRecord).where(TelegramNotificationRecord.id == first).with_for_update())
        assert drain_notifications(factory, settings, sender=lambda settings, payload: 101, pause_seconds=0, now=now + timedelta(seconds=1))["sent"] == 1
        assert claimant.get(TelegramNotificationRecord, first).status == "PENDING"
    with factory() as session:
        assert session.get(TelegramNotificationRecord, second).status == "SENT"
