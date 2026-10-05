"""Registry reads preserve hardware and scope with a fixed number of SQL reads."""
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import event

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.interfaces.http.admin_assets import list_assets, list_endpoints
from assetguard.modules.assets.models import AssetRecord, OrganizationRecord, BuildingRecord, FloorRecord, RoomRecord
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.identity.models import LocationAccessRecord, UserRecord
from assetguard.modules.incidents.models import IncidentRecord
from assetguard.modules.inventory.models import RawInventoryRecord
from assetguard.modules.snapshots.models import ComponentObservationRecord, HardwareSnapshotRecord, ManagedEndpointRecord


def test_registry_batches_unlinked_assets_and_keeps_one_row_per_asset():
    asyncio.run(exercise_registry_query_budget())


async def exercise_registry_query_budget():
    now = datetime.now(UTC)
    factory = get_session_factory()
    with factory() as session:
        organization = OrganizationRecord(name="Query school", created_at=now)
        session.add(organization)
        session.flush()
        assets = [
            AssetRecord(
                organization_id=organization.id, inventory_number=f"QUERY-{index:04d}",
                name=f"Стол {index}", asset_type="Furniture", status="ACTIVE",
                created_at=now, updated_at=now,
            )
            for index in range(216)
        ]
        session.add_all(assets)
        session.flush()
        endpoints = [
            ManagedEndpointRecord(
                source="TEST", asset_id=assets[index].id, organization_id=organization.id,
                hostname=f"query-pc-{index}", status="ONLINE", last_seen_at=now,
                created_at=now, updated_at=now,
            )
            for index in range(2)
        ]
        session.add_all(endpoints)
        session.commit()

    queries = []

    def record_query(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    engine = factory.kw["bind"]
    event.listen(engine, "before_cursor_execute", record_query)
    try:
        transport = httpx.ASGITransport(app=app, client=("registry-budget", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/admin/assets",
                headers={"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret},
            )
    finally:
        event.remove(engine, "before_cursor_execute", record_query)

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 216
    assert len({row["id"] for row in rows}) == 216
    assert rows[0]["inventory_number"] == "QUERY-0000"
    assert rows[0]["organization"] == organization.name
    for index, endpoint in enumerate(endpoints):
        assert rows[index]["endpoint"]["id"] == str(endpoint.id)
    assert all(row["endpoint"] is None for row in rows[2:])
    # Allows fixed authentication/summary reads, but rejects the previous 216 extra lookups.
    assert len(queries) <= 10, len(queries)


def add_snapshot(session, endpoint, captured_at, components=()):
    inventory = RawInventoryRecord(
        managed_endpoint_id=endpoint.id, source="TEST", received_at=captured_at,
        payload_hash=uuid4().hex * 2, payload={}, inventory_type="PARTIAL",
        processing_status="PROCESSED",
    )
    session.add(inventory)
    session.flush()
    snapshot = HardwareSnapshotRecord(
        managed_endpoint_id=endpoint.id, raw_inventory_id=inventory.id,
        captured_at=captured_at, created_at=captured_at, snapshot_type="PARTIAL",
        completeness={}, normalizer_version="test",
    )
    session.add(snapshot)
    session.flush()
    for component_type, model, capacity in components:
        session.add(ComponentObservationRecord(
            hardware_snapshot_id=snapshot.id, component_type=component_type,
            model=model, capacity=capacity, confidence="HIGH", raw_data={},
        ))
    return snapshot


def add_endpoint(session, organization, index, now, room_id=None, linked=True):
    asset = None
    if linked:
        asset = AssetRecord(
            organization_id=organization.id, inventory_number=f"{organization.name}-{index:04d}",
            name=f"PC {index}", asset_type="Desktop", status="ACTIVE", room_id=room_id,
            created_at=now, updated_at=now,
        )
        session.add(asset)
        session.flush()
    endpoint = ManagedEndpointRecord(
        source="TEST", asset_id=asset.id if asset else None, organization_id=organization.id,
        hostname=f"pc-{index}", status="ONLINE", last_seen_at=now + timedelta(seconds=index),
        created_at=now, updated_at=now,
    )
    session.add(endpoint)
    session.flush()
    return endpoint


@pytest.mark.parametrize("endpoint_count", [1, 30])
@pytest.mark.parametrize("path", ["/admin/assets", "/admin/endpoints"])
def test_registry_batches_partial_hardware_and_event_counts(endpoint_count, path):
    now = datetime.now(UTC)
    factory = get_session_factory()
    with factory() as session:
        organization = OrganizationRecord(name="Summary school", created_at=now)
        session.add(organization)
        session.flush()
        endpoints = []
        latest = {}
        for index in range(endpoint_count):
            endpoint = add_endpoint(session, organization, index, now)
            endpoints.append(endpoint)
            old = add_snapshot(session, endpoint, now, [
                ("CPU", f"CPU {index}", None), ("RAM", "Old RAM", 8192),
                ("STORAGE", "Disk A", 256 * 1024**3), ("STORAGE", "Disk B", 128 * 1024**3),
            ])
            add_snapshot(session, endpoint, now + timedelta(seconds=1), [
                ("RAM", "New MiB RAM", 4096), ("RAM", "New byte RAM", 4 * 1024**3),
            ])
            latest[endpoint.id] = add_snapshot(session, endpoint, now + timedelta(seconds=2))
            if index == 0:
                baseline = BaselineRecord(
                    managed_endpoint_id=endpoint.id, hardware_snapshot_id=old.id, status="ACTIVE",
                    accepted_at=now,
                )
                session.add(baseline)
                session.flush()
                for change_status, incident_status in (("OPEN", "OPEN"), ("OPEN", "UNDER_REVIEW"), ("RESOLVED", "RESOLVED")):
                    change = ChangeEventRecord(
                        managed_endpoint_id=endpoint.id, baseline_id=baseline.id,
                        baseline_snapshot_id=old.id, current_snapshot_id=latest[endpoint.id].id,
                        component_type="RAM", event_type="COMPONENT_ADDED", confidence="HIGH",
                        severity="MEDIUM", status=change_status, evidence={}, detected_at=now,
                        detector_version="test", dedup_key=uuid4().hex * 2,
                    )
                    session.add(change)
                    session.flush()
                    session.add(IncidentRecord(
                        managed_endpoint_id=endpoint.id, change_event_id=change.id, status=incident_status,
                        severity="MEDIUM", title="Fixture incident", description="Summary count",
                        created_at=now,
                    ))
        session.commit()

    queries = []

    def record_query(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    engine = factory.kw["bind"]
    event.listen(engine, "before_cursor_execute", record_query)
    try:
        async def read_registry():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
                return await client.get(path, headers={"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret})
        response = asyncio.run(read_registry())
    finally:
        event.remove(engine, "before_cursor_execute", record_query)
    assert response.status_code == 200
    rows = response.json()
    summaries = {row["id"]: row for row in rows} if path.endswith("endpoints") else {row["endpoint"]["id"]: row["endpoint"] for row in rows}
    assert len(rows) == endpoint_count
    for index, endpoint in enumerate(endpoints):
        summary = summaries[str(endpoint.id)]
        assert summary["hardware_summary"] == {
            "ram_bytes": 8 * 1024**3, "ram_modules": 2, "storage_devices": 2, "cpu": f"CPU {index}",
        }
        assert summary["current_snapshot"]["id"] == str(latest[endpoint.id].id)
        assert summary["open_changes"] == (2 if index == 0 else 0)
        assert summary["open_incidents"] == (2 if index == 0 else 0)
    if path.endswith("endpoints"):
        assert [row["id"] for row in rows] == [str(endpoint.id) for endpoint in reversed(endpoints)]
        assert all(row["asset"]["organization"] == organization.name for row in rows)
    # Fixed reads: registry join, bounded snapshots/observations, two grouped counts.
    assert len(queries) <= 5, len(queries)


def test_summary_history_limit_is_per_endpoint_and_keeps_empty_endpoints():
    now = datetime.now(UTC)
    factory = get_session_factory()
    with factory() as session:
        organization = OrganizationRecord(name="History school", created_at=now)
        session.add(organization)
        session.flush()
        old_endpoint = add_endpoint(session, organization, 0, now)
        empty_endpoint = add_endpoint(session, organization, 1, now, linked=False)
        recent_endpoint = add_endpoint(session, organization, 2, now)
        for index in range(51):
            components = []
            if index == 0:
                components = [("CPU", "Outside window", None)]
            elif index == 1:
                components = [("RAM", "At window boundary", 8192)]
            add_snapshot(session, old_endpoint, now + timedelta(seconds=index), components)
        add_snapshot(session, recent_endpoint, now + timedelta(days=1), [("CPU", "Recent CPU", None)])
        session.commit()
        principal = AuthPrincipal(user_id=None, username="test", role="ADMIN", session_id=None, organization_id=organization.id)
        endpoints = {row["id"]: row for row in list_endpoints(session, principal)}
        assets = list_assets(session, principal)
    assert len(assets) == 2 and len(endpoints) == 3
    assert endpoints[str(old_endpoint.id)]["hardware_summary"] == {
        "ram_bytes": 8 * 1024**3, "ram_modules": 1, "storage_devices": 0, "cpu": None,
    }
    assert endpoints[str(recent_endpoint.id)]["hardware_summary"]["cpu"] == "Recent CPU"
    assert endpoints[str(empty_endpoint.id)]["current_snapshot"] is None
    assert endpoints[str(empty_endpoint.id)]["asset"] is None
    assert endpoints[str(empty_endpoint.id)]["hardware_summary"] == {"ram_bytes": 0, "ram_modules": 0, "storage_devices": 0, "cpu": None}


def test_batched_registry_scopes_exclude_foreign_hidden_and_unassigned_endpoints():
    now = datetime.now(UTC)
    with get_session_factory()() as session:
        school = OrganizationRecord(name="Allowed school", created_at=now)
        foreign_school = OrganizationRecord(name="Foreign school", created_at=now)
        session.add_all([school, foreign_school])
        session.flush()
        building = BuildingRecord(organization_id=school.id, name="A", created_at=now)
        session.add(building)
        session.flush()
        floor = FloorRecord(building_id=building.id, name="1", created_at=now)
        session.add(floor)
        session.flush()
        rooms = [RoomRecord(floor_id=floor.id, name=name, created_at=now) for name in ("101", "102")]
        session.add_all(rooms)
        user = UserRecord(username="summary-viewer", password_hash="unused", role="VIEWER", organization_id=school.id, created_at=now)
        session.add(user)
        session.flush()
        session.add(LocationAccessRecord(user_id=user.id, scope_type="ROOM", scope_id=rooms[0].id, permission="VIEWER", created_at=now))
        visible = add_endpoint(session, school, 0, now, room_id=rooms[0].id)
        hidden = add_endpoint(session, school, 1, now, room_id=rooms[1].id)
        unassigned = add_endpoint(session, school, 2, now)
        unlinked = add_endpoint(session, school, 3, now, linked=False)
        foreign = add_endpoint(session, foreign_school, 4, now)
        for endpoint in (visible, hidden, unassigned, unlinked, foreign):
            add_snapshot(session, endpoint, now, [("CPU", f"CPU {endpoint.hostname}", None)])
        session.commit()
        principal = AuthPrincipal(user_id=user.id, username=user.username, role="VIEWER", session_id=None, organization_id=school.id)
        for read in (list_assets, list_endpoints):
            rows = read(session, principal)
            assert len(rows) == 1
            summary = rows[0]["endpoint"] if read is list_assets else rows[0]
            assert summary["id"] == str(visible.id)
            assert summary["hardware_summary"]["cpu"] == "CPU pc-0"
        admin = AuthPrincipal(user_id=None, username="admin", role="ADMIN", session_id=None, organization_id=school.id)
        assert len(list_assets(session, admin)) == 3
        assert len(list_endpoints(session, admin)) == 4
