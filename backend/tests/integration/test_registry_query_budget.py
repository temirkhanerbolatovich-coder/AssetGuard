"""Registry reads must not perform an endpoint lookup for every unlinked asset."""
import asyncio
from datetime import UTC, datetime

import httpx
from sqlalchemy import event

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import AssetRecord, OrganizationRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord


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
