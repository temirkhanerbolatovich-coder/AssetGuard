from __future__ import annotations

import asyncio
import base64
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import OrganizationRecord
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.identity.auth import hash_password
from assetguard.modules.identity.models import AgentCredentialRecord
from assetguard.modules.incidents.models import EndpointHistoryEntryRecord, IncidentRecord
from assetguard.modules.snapshots.models import (
    ComponentObservationRecord, EndpointIdentifierRecord, HardwareSnapshotRecord, ManagedEndpointRecord,
)


def inventory(device: str, uuid: str, name: str = "Original") -> bytes:
    return (
        f"<REQUEST><DEVICEID>{device}</DEVICEID><QUERY>INVENTORY</QUERY><CONTENT>"
        f"<HARDWARE><UUID>{uuid}</UUID><NAME>{name}</NAME></HARDWARE>"
        "<VERSIONCLIENT>1.19</VERSIONCLIENT></CONTENT></REQUEST>"
    ).encode()


def native_headers(username: str, secret: str) -> dict[str, str]:
    encoded = base64.b64encode(f"{username}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Content-Type": "application/xml"}


@pytest.mark.parametrize("case", [
    "bound_duplicate", "bound_new", "foreign_duplicate", "foreign_new",
    "bound_mixed", "foreign_mixed", "bound_unknown",
    "unowned_duplicate", "unowned_new", "claimed_duplicate", "claimed_new",
])
def test_rejected_agent_inventory_cannot_mutate_endpoint_or_identity(case: str) -> None:
    asyncio.run(_reject_out_of_scope_inventory(case))


async def _reject_out_of_scope_inventory(case: str) -> None:
    transport = httpx.ASGITransport(app=app)
    with get_session_factory()() as session:
        school = OrganizationRecord(name="Agent school", created_at=datetime.now(UTC))
        foreign = OrganizationRecord(name="Foreign school", created_at=datetime.now(UTC))
        session.add_all([school, foreign])
        session.commit()
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        shared = native_headers("assetguard", get_settings().inventory_shared_secret)
        for device, uuid in (("scope-a", "SCOPE-UUID-A"), ("scope-b", "SCOPE-UUID-B")):
            assert (await client.post("/glpi-agent", headers=shared, content=inventory(device, uuid))).status_code == 200
        with get_session_factory()() as session:
            endpoints = list(session.scalars(select(ManagedEndpointRecord).order_by(ManagedEndpointRecord.source_agent_id)))
            endpoint_a, endpoint_b = endpoints
            endpoint_a.organization_id = school.id
            endpoint_b.organization_id = None if case.startswith("unowned") else (foreign.id if case.startswith("foreign") else school.id)
            for endpoint in endpoints:
                endpoint.last_seen_at = datetime.now(UTC) - timedelta(days=2)
                endpoint.status = "REQUIRES_VERIFICATION"
            credential = AgentCredentialRecord(
                username="scope-agent", secret_hash=hash_password("scope-test-secret"), status="ACTIVE",
                managed_endpoint_id=None if case.startswith(("foreign", "unowned", "claimed")) else endpoint_a.id,
                organization_id=school.id, issued_at=datetime.now(UTC), revoked_at=None,
            )
            session.add(credential)
            if case.startswith("claimed"):
                session.add(AgentCredentialRecord(username="existing-agent", secret_hash=hash_password("existing-test-secret"),
                    status="ACTIVE", managed_endpoint_id=endpoint_b.id, organization_id=school.id,
                    issued_at=datetime.now(UTC), revoked_at=None))
            session.commit()
            before_endpoints = [(e.id, e.organization_id, e.hostname, e.last_seen_at, e.status, e.updated_at) for e in endpoints]
            before_identifiers = list(session.execute(select(
                EndpointIdentifierRecord.id, EndpointIdentifierRecord.last_seen_at, EndpointIdentifierRecord.is_active,
            ).order_by(EndpointIdentifierRecord.id)))
            protected_models = (HardwareSnapshotRecord, ComponentObservationRecord, EndpointHistoryEntryRecord, IncidentRecord)
            before_counts = [session.scalar(select(func.count()).select_from(model)) for model in protected_models]
            bound_before = credential.managed_endpoint_id
            credential_id = credential.id

        body = inventory("scope-b", "SCOPE-UUID-B", "Changed") if case.endswith("new") else inventory("scope-b", "SCOPE-UUID-B")
        if case.endswith("mixed"):
            body = inventory("scope-b", "SCOPE-UUID-A", "Conflicting")
        if case == "bound_unknown":
            body = inventory("unknown-device", "UNKNOWN-NEW-UUID", "Unknown")
        response = await client.post("/glpi-agent", headers=native_headers("scope-agent", "scope-test-secret"), content=body)
        assert response.status_code == 409, response.text
        with get_session_factory()() as session:
            after = list(session.scalars(select(ManagedEndpointRecord).order_by(ManagedEndpointRecord.source_agent_id)))
            assert [(e.id, e.organization_id, e.hostname, e.last_seen_at, e.status, e.updated_at) for e in after] == before_endpoints
            assert list(session.execute(select(
                EndpointIdentifierRecord.id, EndpointIdentifierRecord.last_seen_at, EndpointIdentifierRecord.is_active,
            ).order_by(EndpointIdentifierRecord.id))) == before_identifiers
            assert [session.scalar(select(func.count()).select_from(model)) for model in protected_models] == before_counts
            assert session.get(AgentCredentialRecord, credential_id).managed_endpoint_id == bound_before
        if case.endswith("new") and not case.startswith("claimed"):
            # A rejected raw payload can later be delivered by its legitimate Agent.
            # It must run the full diff/incident workflow exactly once despite deduplication.
            with get_session_factory()() as session:
                baseline_snapshot = session.scalar(select(HardwareSnapshotRecord).where(HardwareSnapshotRecord.managed_endpoint_id == endpoint_b.id))
                session.add(BaselineRecord(managed_endpoint_id=endpoint_b.id, hardware_snapshot_id=baseline_snapshot.id,
                    status="ACTIVE", accepted_at=datetime.now(UTC), superseded_at=None, reason="test"))
                session.add(AgentCredentialRecord(username="legitimate-agent", secret_hash=hash_password("legitimate-test-secret"),
                    status="ACTIVE", managed_endpoint_id=endpoint_b.id, organization_id=endpoint_b.organization_id,
                    issued_at=datetime.now(UTC), revoked_at=None))
                session.commit()
            for _ in range(2):
                accepted = await client.post("/glpi-agent", headers=native_headers("legitimate-agent", "legitimate-test-secret"), content=body)
                assert accepted.status_code == 200, accepted.text
            with get_session_factory()() as session:
                assert session.scalar(select(func.count()).select_from(ChangeEventRecord)) == 1
                assert session.scalar(select(func.count()).select_from(IncidentRecord)) == 1


@pytest.mark.parametrize("existing_endpoint", [False, True])
def test_scoped_agent_first_inventory_and_duplicate_preserve_organization(existing_endpoint: bool) -> None:
    async def exercise() -> None:
        with get_session_factory()() as session:
            school = OrganizationRecord(name="New Agent school", created_at=datetime.now(UTC))
            session.add(school)
            session.flush()
            credential = AgentCredentialRecord(
                username="new-agent", secret_hash=hash_password("new-test-secret"), status="ACTIVE",
                managed_endpoint_id=None, organization_id=school.id, issued_at=datetime.now(UTC), revoked_at=None,
            )
            session.add(credential)
            session.commit()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            if existing_endpoint:
                seeded = await client.post("/glpi-agent", headers=native_headers("assetguard", get_settings().inventory_shared_secret), content=inventory("new-device", "NEW-SCOPED-UUID"))
                assert seeded.status_code == 200, seeded.text
                with get_session_factory()() as session:
                    endpoint = session.scalars(select(ManagedEndpointRecord)).one()
                    endpoint.organization_id = school.id
                    session.commit()
            for _ in range(2):
                response = await client.post("/glpi-agent", headers=native_headers("new-agent", "new-test-secret"), content=inventory("new-device", "NEW-SCOPED-UUID"))
                assert response.status_code == 200, response.text
        with get_session_factory()() as session:
            endpoint = session.scalars(select(ManagedEndpointRecord)).one()
            assert endpoint.organization_id == school.id
            assert session.get(AgentCredentialRecord, credential.id).managed_endpoint_id == endpoint.id
            assert session.scalar(select(func.count()).select_from(HardwareSnapshotRecord)) == 1
    asyncio.run(exercise())
