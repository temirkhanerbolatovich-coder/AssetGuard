"""Delivery visibility respects tenant boundaries and never exposes transport payloads."""
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import OrganizationRecord
from assetguard.modules.identity.auth import create_session, hash_password
from assetguard.modules.identity.models import UserRecord
from assetguard.modules.notifications.models import TelegramNotificationRecord


def test_notification_pages_filter_scope_and_redact_payload():
    async def exercise():
        now = datetime.now(UTC)
        with get_session_factory()() as session:
            own = OrganizationRecord(name="Own", created_at=now)
            foreign = OrganizationRecord(name="Foreign", created_at=now)
            session.add_all([own, foreign])
            session.flush()
            admin = UserRecord(username="queue-admin", password_hash=hash_password("test-password"),
                role="ADMIN", organization_id=own.id, is_active=True, created_at=now)
            session.add(admin)
            session.flush()
            token = create_session(session, admin)
            for index, (organization_id, status, attempts) in enumerate([
                (own.id, "PENDING", 0), (own.id, "PENDING", 2), (own.id, "SENT", 1),
                (foreign.id, "PENDING", 3), (None, "PENDING", 1),
            ]):
                session.add(TelegramNotificationRecord(event_key=f"secret-event-{index}",
                    organization_id=organization_id, room_id=None, status=status, attempts=attempts,
                    payload={"route": f"#incident={uuid4()}" if not attempts else "https://invalid.example/secret",
                             "subject": "private-body", "chat_id": "private-recipient"},
                    created_at=now, next_attempt_at=now, sent_at=now if status == "SENT" else None,
                    telegram_message_id=123, last_error_code="private-error-detail" if attempts else None))
            session.commit()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            headers = {"X-AssetGuard-Admin-Token": token}
            first = await client.get("/admin/notifications?limit=1", headers=headers)
            assert first.status_code == 200
            body = first.json()
            assert body["summary"] == {"pending": 1, "retrying": 1, "sent": 1}
            assert body["total"] == 3 and len(body["items"]) == 1
            second = (await client.get("/admin/notifications?limit=1&offset=1", headers=headers)).json()
            assert second["items"][0]["id"] != body["items"][0]["id"]
            retry = await client.get("/admin/notifications?status=RETRYING", headers=headers)
            assert retry.json()["total"] == 1
            item = retry.json()["items"][0]
            assert item["attempts"] == 2 and item["route"] is None and item["last_error_code"] == "UNKNOWN_ERROR"
            for value in ("private-body", "private-recipient", "private-error-detail", "secret-event", "telegram_message_id"):
                assert value not in retry.text
            sent = (await client.get("/admin/notifications?status=SENT", headers=headers)).json()["items"][0]
            assert sent["next_attempt_at"] is None and sent["sent_at"]
            pending = (await client.get("/admin/notifications?status=PENDING", headers=headers)).json()
            assert pending["total"] == 1 and pending["items"][0]["route"].startswith("#incident=")
            for query in ("limit=0", "limit=101", "offset=-1", "status=FAILED"):
                assert (await client.get(f"/admin/notifications?{query}", headers=headers)).status_code == 422
            platform = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
            assert (await client.get("/admin/notifications", headers=platform)).json()["total"] == 5
            assert (await client.get("/admin/notifications")).status_code == 401
            with get_session_factory()() as session:
                user = session.get(UserRecord, admin.id)
                user.role = "VIEWER"
                session.commit()
            # Existing admin dependencies deliberately return 401 for a non-admin role.
            assert (await client.get("/admin/notifications", headers=headers)).status_code == 401
    asyncio.run(exercise())
