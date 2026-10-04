from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from assetguard.app import app
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import (
    AssetRecord, BuildingRecord, FloorRecord, OrganizationRecord,
    RoomInspectionItemRecord, RoomInspectionRecord, RoomRecord,
)
from assetguard.modules.identity.auth import hash_password
from assetguard.modules.identity.models import LocationAccessRecord, UserRecord
from assetguard.modules.incidents.models import PhysicalIncidentRecord


def test_physical_incident_list_and_evidence_respect_tenant_and_room_grants():
    asyncio.run(_check_physical_reads())


async def _check_physical_reads():
    now = datetime.now(UTC)
    factory = get_session_factory()
    with factory() as session:
        organizations = [OrganizationRecord(name=name, created_at=now) for name in ("School A", "School B")]
        session.add_all(organizations)
        session.flush()
        rooms, incidents = [], []
        for index, organization in enumerate((organizations[0], organizations[0], organizations[1])):
            building = BuildingRecord(organization_id=organization.id, name=f"Building {index}", created_at=now)
            session.add(building); session.flush()
            floor = FloorRecord(building_id=building.id, name="1", created_at=now)
            session.add(floor); session.flush()
            room = RoomRecord(floor_id=floor.id, name=f"Room {index}", created_at=now)
            session.add(room); session.flush()
            asset = AssetRecord(organization_id=organization.id, room_id=room.id,
                inventory_number=f"INV-{index}", name=f"Desk {index}", asset_type="Furniture",
                category="FURNITURE", tracking_mode="GROUPED", quantity=3, unit="шт.",
                status="ACTIVE", created_at=now, updated_at=now)
            session.add(asset); session.flush()
            inspection = RoomInspectionRecord(room_id=room.id, inspector_name="Inspector", comment="Original report", completed_at=now)
            session.add(inspection); session.flush()
            item = RoomInspectionItemRecord(inspection_id=inspection.id, asset_id=asset.id,
                result="MISSING", expected_quantity=3, affected_quantity=1, comment="One desk missing")
            session.add(item); session.flush()
            incident = PhysicalIncidentRecord(room_id=room.id, asset_id=asset.id, inspection_item_id=item.id,
                issue_type="MISSING", affected_quantity=1, status="OPEN", severity="HIGH",
                title="Missing desk", description="Inspection evidence", created_at=now)
            session.add(incident); session.flush()
            rooms.append(room.id); incidents.append(str(incident.id))
        users = [UserRecord(username=f"reads-{role.lower()}-{uuid4().hex[:8]}",
            password_hash=hash_password("Read-test-password-123"), role=role,
            organization_id=organizations[0].id, is_active=True, created_at=now) for role in ("VIEWER", "ADMIN")]
        session.add_all(users); session.commit()
        viewer_id = users[0].id
        names = [user.username for user in users]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        endpoint = "/admin/locations/physical-incidents"
        assert (await client.get(endpoint)).status_code == 401
        credentials = []
        for name in names:
            response = await client.post("/auth/login", json={"username": name, "password": "Read-test-password-123"})
            assert response.status_code == 200
            credentials.append({"X-AssetGuard-Admin-Token": response.json()["access_token"]})
        viewer, admin = credentials
        assert (await client.get(endpoint, headers=viewer)).json() == []
        assert (await client.get(f"{endpoint}/{incidents[0]}", headers=viewer)).status_code == 404
        with factory() as session:
            # Even an inconsistent foreign-room grant must not bypass the tenant boundary.
            session.add_all([LocationAccessRecord(user_id=viewer_id, scope_type="ROOM", scope_id=room_id,
                permission="VIEWER", created_at=now) for room_id in (rooms[0], rooms[2])])
            session.commit()
        response = await client.get(endpoint, headers=viewer)
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [incidents[0]]
        assert "evidence" not in response.json()[0]
        detail = await client.get(f"{endpoint}/{incidents[0]}", headers=viewer)
        assert detail.status_code == 200
        evidence = detail.json()["evidence"]
        assert evidence["expected_quantity"] == 3 and evidence["affected_quantity"] == 1
        assert evidence["result"] == "MISSING" and evidence["comment"] == "One desk missing"
        assert evidence["inspector_name"] == "Inspector"
        assert detail.json()["decisions"] == []
        for incident_id in incidents[1:]:
            assert (await client.get(f"{endpoint}/{incident_id}", headers=viewer)).status_code == 404
        assert {item["id"] for item in (await client.get(endpoint, headers=admin)).json()} == set(incidents[:2])
        assert (await client.get(f"{endpoint}/{incidents[2]}", headers=admin)).status_code == 404
        assert (await client.get(f"{endpoint}/{uuid4()}", headers=admin)).status_code == 404
        assert (await client.get(f"{endpoint}/invalid", headers=admin)).status_code == 422
        assert (await client.post(f"{endpoint}/{incidents[0]}/decision", headers=viewer,
            json={"action": "REPAIR", "comment": "Denied"})).status_code == 404
