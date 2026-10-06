import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import AssetRecord, BuildingRecord, FloorRecord, OrganizationRecord, RoomRecord
from assetguard.modules.identity.auth import hash_password
from assetguard.modules.identity.models import LocationAccessRecord, UserRecord
from assetguard.modules.incidents.models import EndpointHistoryEntryRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord


@pytest.mark.parametrize("role", ["ADMIN", "VIEWER", "LOCATION_MANAGER", "INVENTORY_CLERK"])
def test_read_routes_agree_on_freshness_without_mutations_or_tenant_leaks(monkeypatch, role):
    monkeypatch.setenv("ASSETGUARD_ENDPOINT_STALE_AFTER_HOURS", "7")
    get_settings.cache_clear()
    try:
        asyncio.run(_exercise_read_routes(role))
    finally:
        get_settings.cache_clear()


async def _exercise_read_routes(role):
    now = datetime.now(UTC)
    factory = get_session_factory()
    with factory() as session:
        organization = OrganizationRecord(name="Freshness School", created_at=now)
        foreign = OrganizationRecord(name="Other School", created_at=now)
        session.add_all([organization, foreign]); session.flush()
        building = BuildingRecord(organization_id=organization.id, name="Корпус", created_at=now)
        session.add(building); session.flush()
        floor = FloorRecord(building_id=building.id, name="1", created_at=now)
        session.add(floor); session.flush()
        room = RoomRecord(floor_id=floor.id, name="101", created_at=now)
        session.add(room); session.flush()
        expected = {}
        asset_ids = {}
        for name, age, stored_status, connection in [
            ("fresh", 1, "ONLINE", "ONLINE"), ("old", 8, "ONLINE", "STALE"),
            ("offline", 8, "OFFLINE", "OFFLINE"), ("conflict", 8, "IDENTITY_CONFLICT", "IDENTITY_CONFLICT"),
        ]:
            asset = AssetRecord(organization_id=organization.id, room_id=room.id, inventory_number=name,
                name=name, asset_type="Desktop", category="IT", tracking_mode="INDIVIDUAL", quantity=1,
                unit="шт.", status="ACTIVE", created_at=now, updated_at=now)
            session.add(asset); session.flush()
            endpoint = ManagedEndpointRecord(organization_id=organization.id, asset_id=asset.id,
                source="TEST", hostname=name, status=stored_status, last_seen_at=now-timedelta(hours=age),
                created_at=now, updated_at=now)
            session.add(endpoint); session.flush()
            expected[str(endpoint.id)] = (stored_status, connection)
            asset_ids[str(endpoint.id)] = str(asset.id)
        hidden = ManagedEndpointRecord(organization_id=foreign.id, source="TEST", hostname="hidden",
            status="ONLINE", last_seen_at=now-timedelta(days=5), created_at=now, updated_at=now)
        user = UserRecord(username="freshness-user", password_hash=hash_password("freshness-password-123"),
            role=role, organization_id=organization.id, is_active=True, created_at=now)
        session.add_all([hidden, user]); session.flush()
        session.add(LocationAccessRecord(user_id=user.id, scope_type="ROOM", scope_id=room.id,
            permission="VIEWER", created_at=now))
        session.commit()
        room_id, hidden_id = room.id, hidden.id

    def check_endpoint(item):
        assert (item["status"], item["connection_status"]) == expected[item["id"]]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        login = await client.post("/auth/login", json={"username": "freshness-user", "password": "freshness-password-123"})
        assert login.status_code == 200, login.text
        headers = {"X-AssetGuard-Admin-Token": login.json()["access_token"]}
        for path, key in [("/admin/endpoints", None), ("/admin/assets", "endpoint"),
                          (f"/admin/locations/rooms/{room_id}/workspace", "agents")]:
            response = await client.get(path, headers=headers)
            assert response.status_code == 200, response.text
            payload = response.json()
            items = payload["agents"] if key == "agents" else [item["endpoint"] for item in payload] if key == "endpoint" else payload
            assert {item["id"] for item in items} == set(expected)
            for item in items:
                check_endpoint(item)
        for endpoint_id, asset_id in asset_ids.items():
            detail = await client.get(f"/admin/endpoints/{endpoint_id}", headers=headers)
            asset = await client.get(f"/admin/assets/{asset_id}", headers=headers)
            assert detail.status_code == asset.status_code == 200
            check_endpoint(detail.json()); check_endpoint(asset.json()["endpoint"])
        operations = await client.get("/admin/operations/status", headers=headers)
        assert operations.status_code == 200, operations.text
        agents = operations.json()["agents"]
        assert {key: agents[key] for key in ("total", "online", "stale", "offline", "identity_conflicts", "stale_after_hours")} == {
            "total": 4, "online": 1, "stale": 1, "offline": 1, "identity_conflicts": 1, "stale_after_hours": 7,
        }
        assert (await client.get(f"/admin/endpoints/{hidden_id}", headers=headers)).status_code == 404
    with factory() as session:
        for endpoint in session.scalars(select(ManagedEndpointRecord).where(ManagedEndpointRecord.id != hidden_id)):
            assert endpoint.status == expected[str(endpoint.id)][0]
            assert endpoint.updated_at == now
        assert session.scalar(select(func.count()).select_from(EndpointHistoryEntryRecord)) == 0
