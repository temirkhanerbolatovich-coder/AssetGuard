from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import AssetRecord, OrganizationRecord
from assetguard.modules.inventory.models import RawInventoryRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord
from assetguard.modules.vision.models import VisionRoomRecord


def test_tenant_cannot_read_another_organization_by_uuid() -> None:
    asyncio.run(_exercise_tenant_isolation())


async def _exercise_tenant_isolation() -> None:
    now = datetime.now(UTC)
    factory = get_session_factory()
    with factory() as session:
        school_a = OrganizationRecord(name="Isolation School A", created_at=now)
        school_b = OrganizationRecord(name="Isolation School B", created_at=now)
        session.add_all([school_a, school_b]); session.flush()
        asset_b = AssetRecord(organization_id=school_b.id, inventory_number="B-001", name="Hidden PC", asset_type="Desktop", status="ACTIVE", building=None, floor=None, room="101", notes=None, created_at=now, updated_at=now)
        session.add(asset_b); session.flush()
        endpoint_b = ManagedEndpointRecord(source="TEST", source_agent_id="tenant-b", asset_id=asset_b.id, organization_id=school_b.id, hostname="hidden-b", last_seen_at=now, status="ONLINE", created_at=now, updated_at=now)
        session.add(endpoint_b); session.flush()
        inventory_b = RawInventoryRecord(managed_endpoint_id=endpoint_b.id, source="TEST", source_version=None, schema_version=None, received_at=now, payload_hash="b" * 64, payload={"content": {}}, inventory_type="PARTIAL", processing_status="PROCESSED", processing_error=None, ingest_idempotency_key="tenant-isolation-b")
        room_b = VisionRoomRecord(name="101", organization_id=school_b.id, created_at=now)
        session.add_all([inventory_b, room_b]); session.commit()

    bootstrap = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        user = await client.post("/admin/users", headers=bootstrap, json={"username": "tenant-a-viewer", "password": "tenant-isolation-password", "role": "VIEWER", "organization_id": str(school_a.id)})
        assert user.status_code == 201, user.text
        login = await client.post("/auth/login", json={"username": "tenant-a-viewer", "password": "tenant-isolation-password"})
        assert login.status_code == 200
        headers = {"X-AssetGuard-Admin-Token": login.json()["access_token"]}
        for path in (f"/admin/assets/{asset_b.id}", f"/admin/endpoints/{endpoint_b.id}", f"/admin/inventories/{inventory_b.id}", f"/admin/vision/rooms/{room_b.id}/scans"):
            response = await client.get(path, headers=headers)
            assert response.status_code == 404, (path, response.status_code, response.text)
