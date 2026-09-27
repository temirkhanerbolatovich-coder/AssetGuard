from __future__ import annotations

import asyncio
import base64
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.identity.models import AgentReenrolmentRecord

PROLOG = b"""<?xml version='1.0' encoding='UTF-8'?>
<REQUEST><DEVICEID>reenrol-fixture-pc</DEVICEID><QUERY>PROLOG</QUERY></REQUEST>"""

INVENTORY = b"""<?xml version='1.0' encoding='UTF-8'?>
<REQUEST><CONTENT>
  <BIOS><BSERIAL>REENROL-BIOS</BSERIAL></BIOS>
  <HARDWARE><UUID>REENROL-UUID-001</UUID><NAME>reenrol-fixture-pc</NAME></HARDWARE>
  <CPUS><NAME>Fixture CPU</NAME></CPUS>
  <MEMORIES><SERIALNUMBER>REENROL-RAM</SERIALNUMBER><NUMSLOTS>DIMM 0</NUMSLOTS><CAPACITY>8192</CAPACITY></MEMORIES>
  <STORAGES><SERIAL>REENROL-SSD</SERIAL><MODEL>Fixture SSD</MODEL><DISKSIZE>512000</DISKSIZE></STORAGES>
  <NETWORKS><MACADDR>02:00:00:00:91:01</MACADDR></NETWORKS>
  <VERSIONCLIENT>1.20</VERSIONCLIENT>
</CONTENT><DEVICEID>reenrol-fixture-pc</DEVICEID><QUERY>INVENTORY</QUERY></REQUEST>"""


def test_admin_approved_reenrolment_rotates_credential_without_plaintext_storage() -> None:
    asyncio.run(_exercise_admin_approved_reenrolment())


async def _exercise_admin_approved_reenrolment() -> None:
    admin = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post("/admin/agent-credentials", headers=admin)
        issued = created.json()
        old_basic = base64.b64encode(f"{issued['username']}:{issued['secret']}".encode()).decode()
        old_headers = {"Authorization": f"Basic {old_basic}", "Content-Type": "application/xml"}
        assert (await client.post("/glpi-agent", headers=old_headers, content=INVENTORY)).status_code == 200

        requested = await client.post("/agent/re-enrolments", json={
            "identifier_type": "SMBIOS_UUID",
            "identifier_value": " reenrol-uuid-001 ",
            "computer_name": "REENROL-PC",
            "installer_version": "0.1.7",
        })
        assert requested.status_code == 202, requested.text
        request_body = requested.json()
        assert set(request_body) == {"id", "claim_token", "status", "expires_at"}
        assert len(request_body["claim_token"]) >= 32
        with get_session_factory()() as session:
            stored_request = session.get(AgentReenrolmentRecord, UUID(request_body["id"]))
            assert stored_request is not None
            assert stored_request.token_hash != request_body["claim_token"]
            assert stored_request.credential_secret_hash != request_body["claim_token"]
            assert request_body["claim_token"] not in vars(stored_request).values()
        poll_headers = {"X-AssetGuard-Reenrolment-Token": request_body["claim_token"]}
        assert (await client.get(f"/agent/re-enrolments/{request_body['id']}", headers={
            "X-AssetGuard-Reenrolment-Token": "x" * 40,
        })).status_code == 404

        pending = await client.get("/admin/agent-re-enrolments", headers=admin)
        pending_item = next(item for item in pending.json() if item["id"] == request_body["id"])
        assert pending_item["status"] == "PENDING"
        assert pending_item["identifier_value"] == "REENROL-UUID-001"
        assert pending_item["endpoint_id"] is not None
        assert "claim_token" not in pending_item

        approved = await client.post(
            f"/admin/agent-re-enrolments/{request_body['id']}/approve", headers=admin,
        )
        assert approved.status_code == 200, approved.text
        assert (await client.post(
            f"/admin/agent-re-enrolments/{request_body['id']}/approve", headers=admin,
        )).status_code == 409
        assert (await client.post("/glpi-agent", headers=old_headers, content=PROLOG)).status_code == 401

        status = await client.get(f"/agent/re-enrolments/{request_body['id']}", headers=poll_headers)
        assert status.status_code == 200
        assert status.json()["status"] == "APPROVED"
        new_username = status.json()["agent_username"]
        new_basic = base64.b64encode(f"{new_username}:{request_body['claim_token']}".encode()).decode()
        new_headers = {"Authorization": f"Basic {new_basic}", "Content-Type": "application/xml"}
        assert (await client.post("/glpi-agent", headers=new_headers, content=PROLOG)).status_code == 200

        credentials = (await client.get("/admin/agent-credentials", headers=admin)).json()
        assert sum(item["status"] == "ACTIVE" for item in credentials) == 1
        assert sum(item["status"] == "REVOKED" for item in credentials) == 1
        active = next(item for item in credentials if item["status"] == "ACTIVE")
        revoked = next(item for item in credentials if item["status"] == "REVOKED")
        assert active["endpoint_id"] == revoked["endpoint_id"] == approved.json()["endpoint_id"]


def test_unmatched_reenrolment_requires_admin_rejection() -> None:
    asyncio.run(_exercise_unmatched_reenrolment())


async def _exercise_unmatched_reenrolment() -> None:
    admin = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        invalid_name = await client.post("/agent/re-enrolments", json={
            "identifier_type": "SMBIOS_UUID",
            "identifier_value": "UNKNOWN-REENROL-UUID",
            "computer_name": "   ",
            "installer_version": "0.1.7",
        })
        assert invalid_name.status_code == 422
        requested = await client.post("/agent/re-enrolments", json={
            "identifier_type": "SMBIOS_UUID",
            "identifier_value": "UNKNOWN-REENROL-UUID",
            "computer_name": "UNKNOWN-PC",
            "installer_version": "0.1.7",
        })
        body = requested.json()
        assert requested.status_code == 202
        assert (await client.post(
            f"/admin/agent-re-enrolments/{body['id']}/approve", headers=admin,
        )).status_code == 409
        rejected = await client.post(
            f"/admin/agent-re-enrolments/{body['id']}/reject", headers=admin,
        )
        assert rejected.status_code == 200
        polled = await client.get(f"/agent/re-enrolments/{body['id']}", headers={
            "X-AssetGuard-Reenrolment-Token": body["claim_token"],
        })
        assert polled.json()["status"] == "REJECTED"


def test_expired_reenrolment_cannot_be_approved() -> None:
    asyncio.run(_exercise_expired_reenrolment())


async def _exercise_expired_reenrolment() -> None:
    admin = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        requested = await client.post("/agent/re-enrolments", json={
            "identifier_type": "SMBIOS_UUID",
            "identifier_value": "EXPIRED-REENROL-UUID",
            "computer_name": "EXPIRED-PC",
            "installer_version": "0.1.7",
        })
        body = requested.json()
        with get_session_factory()() as session:
            stored_request = session.get(AgentReenrolmentRecord, UUID(body["id"]))
            assert stored_request is not None
            stored_request.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            session.commit()

        polled = await client.get(f"/agent/re-enrolments/{body['id']}", headers={
            "X-AssetGuard-Reenrolment-Token": body["claim_token"],
        })
        assert polled.json()["status"] == "EXPIRED"
        assert (await client.post(
            f"/admin/agent-re-enrolments/{body['id']}/approve", headers=admin,
        )).status_code == 409
