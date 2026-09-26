from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import AssetRecord, BuildingRecord, FloorRecord, OrganizationRecord, RoomRecord
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.incidents.models import EndpointHistoryEntryRecord, IncidentRecord
from assetguard.modules.inventory.models import RawInventoryRecord
from assetguard.modules.identity.auth import hash_password
from assetguard.modules.identity.models import AgentCredentialRecord, UserRecord
from assetguard.modules.snapshots.models import HardwareSnapshotRecord, ManagedEndpointRecord
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
        building_b = BuildingRecord(organization_id=school_b.id, name="Hidden building", created_at=now)
        session.add(building_b); session.flush()
        floor_b = FloorRecord(building_id=building_b.id, name="1", created_at=now)
        session.add(floor_b); session.flush()
        room_location_b = RoomRecord(floor_id=floor_b.id, name="101", created_at=now)
        session.add(room_location_b); session.flush()
        asset_b = AssetRecord(organization_id=school_b.id, inventory_number="B-001", name="Hidden PC", asset_type="Desktop", status="ACTIVE", building=None, floor=None, room="101", notes=None, created_at=now, updated_at=now)
        session.add(asset_b); session.flush()
        endpoint_b = ManagedEndpointRecord(source="TEST", source_agent_id="tenant-b", asset_id=asset_b.id, organization_id=school_b.id, hostname="hidden-b", last_seen_at=now, status="ONLINE", created_at=now, updated_at=now)
        session.add(endpoint_b); session.flush()
        inventory_b = RawInventoryRecord(managed_endpoint_id=endpoint_b.id, source="TEST", source_version=None, schema_version=None, received_at=now, payload_hash="b" * 64, payload={"content": {}}, inventory_type="PARTIAL", processing_status="PROCESSED", processing_error=None, ingest_idempotency_key="tenant-isolation-b")
        room_b = VisionRoomRecord(name="101", organization_id=school_b.id, created_at=now)
        session.add_all([inventory_b, room_b]); session.flush()
        snapshot_b = HardwareSnapshotRecord(managed_endpoint_id=endpoint_b.id, raw_inventory_id=inventory_b.id, captured_at=now, created_at=now, snapshot_type="FULL", completeness={}, normalizer_version="test")
        session.add(snapshot_b); session.flush()
        baseline_b = BaselineRecord(managed_endpoint_id=endpoint_b.id, hardware_snapshot_id=snapshot_b.id, status="ACTIVE", accepted_at=now, superseded_at=None, reason=None)
        session.add(baseline_b); session.flush()
        change_b = ChangeEventRecord(managed_endpoint_id=endpoint_b.id, baseline_id=baseline_b.id, baseline_snapshot_id=snapshot_b.id, current_snapshot_id=snapshot_b.id, component_type="RAM", previous_observation_id=None, current_observation_id=None, event_type="COMPONENT_ADDED", confidence="HIGH", severity="MEDIUM", status="OPEN", evidence={}, detected_at=now, detector_version="test", dedup_key="b" * 64)
        session.add(change_b); session.flush()
        incident_b = IncidentRecord(managed_endpoint_id=endpoint_b.id, change_event_id=change_b.id, status="OPEN", severity="MEDIUM", title="Hidden incident", description="Tenant B only", created_at=now, resolved_at=None)
        history_b = EndpointHistoryEntryRecord(managed_endpoint_id=endpoint_b.id, event_type="TEST", occurred_at=now, related_entity_type="SNAPSHOT", related_entity_id=snapshot_b.id, message="Tenant B only", metadata_json={})
        foreign_user = UserRecord(
            username="tenant-b-admin", password_hash=hash_password("tenant-isolation-password"),
            role="ADMIN", organization_id=school_b.id, is_active=True, created_at=now,
        )
        foreign_credential = AgentCredentialRecord(
            username="tenant-b-agent", secret_hash=hash_password("tenant-isolation-secret"),
            status="ACTIVE", managed_endpoint_id=None, organization_id=school_b.id,
            issued_at=now, revoked_at=None,
        )
        session.add_all([incident_b, history_b, foreign_user, foreign_credential]); session.commit()

    bootstrap = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
    transport = httpx.ASGITransport(app=app, client=("tenant-isolation", 50000))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        user = await client.post("/admin/users", headers=bootstrap, json={"username": "tenant-a-admin", "password": "tenant-isolation-password", "role": "ADMIN", "organization_id": str(school_a.id)})
        assert user.status_code == 201, user.text
        login = await client.post("/auth/login", json={"username": "tenant-a-admin", "password": "tenant-isolation-password"})
        assert login.status_code == 200
        headers = {"X-AssetGuard-Admin-Token": login.json()["access_token"]}

        foreign_login = await client.post("/auth/login", json={"username": "tenant-b-admin", "password": "tenant-isolation-password"})
        assert foreign_login.status_code == 200
        foreign_headers = {"X-AssetGuard-Admin-Token": foreign_login.json()["access_token"]}
        foreign_sessions = await client.get("/admin/sessions", headers=foreign_headers)
        assert foreign_sessions.status_code == 200
        foreign_session_id = foreign_sessions.json()[0]["id"]

        async def assert_not_listed(path: str, resource_id: str) -> None:
            response = await client.get(path, headers=headers)
            assert response.status_code == 200, (path, response.text)
            assert resource_id not in {item["id"] for item in response.json()}, path

        for path, resource_id in (
            ("/admin/assets", str(asset_b.id)),
            ("/admin/endpoints", str(endpoint_b.id)),
            ("/admin/inventories", str(inventory_b.id)),
            ("/admin/changes", str(change_b.id)),
            ("/admin/incidents", str(incident_b.id)),
            ("/admin/vision/rooms", str(room_b.id)),
            ("/admin/users", str(foreign_user.id)),
            ("/admin/agent-credentials", str(foreign_credential.id)),
        ):
            await assert_not_listed(path, resource_id)
        organizations = await client.get("/admin/locations/organizations", headers=headers)
        assert organizations.status_code == 200
        assert str(school_b.id) not in {item["id"] for item in organizations.json()}
        sessions = await client.get("/admin/sessions", headers=headers)
        assert sessions.status_code == 200
        assert foreign_session_id not in {item["id"] for item in sessions.json()}
        operations = await client.get("/admin/operations/status", headers=headers)
        assert operations.status_code == 200
        assert operations.json()["agents"]["total"] == 0

        for path in (
            f"/admin/assets/{asset_b.id}", f"/admin/assets/{asset_b.id}/qr.svg",
            f"/admin/endpoints/{endpoint_b.id}", f"/admin/inventories/{inventory_b.id}",
            f"/admin/endpoints/{endpoint_b.id}/snapshots", f"/admin/snapshots/{snapshot_b.id}",
            f"/admin/endpoints/{endpoint_b.id}/baseline", f"/admin/changes/{change_b.id}",
            f"/admin/incidents/{incident_b.id}", f"/admin/endpoints/{endpoint_b.id}/history",
            f"/admin/vision/rooms/{room_b.id}/scans",
        ):
            response = await client.get(path, headers=headers)
            assert response.status_code == 404, (path, response.status_code, response.text)
        baseline = await client.post(f"/admin/snapshots/{snapshot_b.id}/baseline", headers=headers, json={"reason": "not allowed"})
        assert baseline.status_code == 404, baseline.text
        decision = await client.post(f"/admin/incidents/{incident_b.id}/decision", headers=headers, json={"classification": "REPAIR"})
        assert decision.status_code == 404, decision.text
        assert (await client.patch(f"/admin/users/{foreign_user.id}", headers=headers, json={"active": False})).status_code == 404
        assert (await client.delete(f"/admin/sessions/{foreign_session_id}", headers=headers)).status_code == 404
        assert (await client.post(f"/admin/agent-credentials/{foreign_credential.id}/revoke", headers=headers)).status_code == 404
        assert (await client.post(f"/admin/locations/buildings/{building_b.id}/floors", headers=headers, json={"name": "2"})).status_code == 404
        assert (await client.post(f"/admin/locations/floors/{floor_b.id}/rooms", headers=headers, json={"name": "102"})).status_code == 404
        assert (await client.patch(f"/admin/locations/rooms/{room_location_b.id}", headers=headers, json={"purpose": "Forbidden"})).status_code == 404
        assert (await client.post(f"/admin/endpoints/{endpoint_b.id}/asset/{asset_b.id}", headers=headers)).status_code == 404
        foreign_scan = await client.post(
            "/admin/vision/scans", headers=headers, data={"asset_id": str(asset_b.id)},
            files={"image": ("forbidden.jpg", b"not-a-real-image", "image/jpeg")},
        )
        assert foreign_scan.status_code == 404
