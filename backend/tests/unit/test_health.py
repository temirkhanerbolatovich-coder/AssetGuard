import asyncio
from datetime import UTC, datetime, timedelta

import httpx

from assetguard.app import app
from assetguard.interfaces.http.health import _existing_storage_path, operations_status
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import OrganizationRecord
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.snapshots.models import ManagedEndpointRecord


def test_health_reports_service_status() -> None:
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "assetguard",
        "version": "0.1.0",
    }


def test_readiness_checks_database() -> None:
    async def request_readiness() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/health/ready")

    response = asyncio.run(request_readiness())

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "assetguard"}


def test_storage_probe_uses_nearest_existing_ancestor(tmp_path) -> None:
    storage_root = tmp_path / ".local" / "vision"

    assert _existing_storage_path(storage_root) == tmp_path


def test_operations_counts_expired_agents_without_mutating_status_or_leaking_tenants() -> None:
    now = datetime.now(UTC)
    stale = now - timedelta(hours=get_settings().endpoint_stale_after_hours + 1)
    with get_session_factory()() as session:
        own = OrganizationRecord(name="Monitoring own", created_at=now)
        foreign = OrganizationRecord(name="Monitoring foreign", created_at=now)
        session.add_all([own, foreign])
        session.flush()
        endpoints = [
            ManagedEndpointRecord(source="TEST", organization_id=organization.id, hostname=str(index),
                status=status, last_seen_at=last_seen, created_at=now, updated_at=now)
            for index, (organization, status, last_seen) in enumerate([
                (own, "ONLINE", now), (own, "ONLINE", stale),
                (own, "REQUIRES_VERIFICATION", stale), (own, "IDENTITY_CONFLICT", stale),
                (own, "OFFLINE", stale), (foreign, "ONLINE", stale),
            ])
        ]
        session.add_all(endpoints)
        session.commit()
        before = [(e.status, e.last_seen_at, e.updated_at) for e in endpoints]
        principal = AuthPrincipal(user_id=None, username="monitor", role="ADMIN", session_id=None, organization_id=own.id)
        agents = operations_status(session, principal)["agents"]
        assert agents == {"total": 5, "online": 1, "offline": 1, "stale": 2, "identity_conflicts": 1, "last_inventory_at": None, "stale_after_hours": get_settings().endpoint_stale_after_hours}
        for endpoint in endpoints:
            session.refresh(endpoint)
        assert [(e.status, e.last_seen_at, e.updated_at) for e in endpoints] == before
