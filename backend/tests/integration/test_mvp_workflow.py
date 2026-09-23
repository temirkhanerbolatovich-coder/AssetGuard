from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import httpx
from assetguard.app import app
from assetguard.infrastructure.config import get_settings

FIXTURES = Path(__file__).parents[1] / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def ingest_headers(key: str, inventory_type: str = "FULL") -> dict[str, str]:
    return {
        "X-AssetGuard-Ingest-Token": get_settings().inventory_shared_secret,
        "X-AssetGuard-Idempotency-Key": key,
        "X-AssetGuard-Source": "GLPI_AGENT",
        "X-AssetGuard-Source-Version": "1.19",
        "X-AssetGuard-Schema-Version": "automated-fixture-v1",
        "X-AssetGuard-Inventory-Type": inventory_type,
    }


def admin_headers() -> dict[str, str]:
    return {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}


def test_complete_mvp_workflow_and_required_fixtures() -> None:
    asyncio.run(_complete_mvp_workflow())


async def _complete_mvp_workflow() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        initial = fixture("glpi-agent-minimal-sanitized.json")
        response = await client.post("/internal/inventories", headers=ingest_headers(uuid4().hex), json=initial)
        assert response.status_code == 202
        first_snapshot_id = response.json()["snapshot_id"]
        first_snapshot = (await client.get(f"/admin/snapshots/{first_snapshot_id}", headers=admin_headers())).json()
        endpoint_id = first_snapshot["endpoint_id"]

        asset_response = await client.post("/admin/assets", headers=admin_headers(), json={
            "inventory_number": "PC-E2E-001", "name": "E2E workstation", "asset_type": "Desktop",
        })
        assert asset_response.status_code == 201
        asset_id = asset_response.json()["id"]
        assert (await client.post(f"/admin/endpoints/{endpoint_id}/asset/{asset_id}", headers=admin_headers())).status_code == 200
        assert (await client.post(f"/admin/snapshots/{first_snapshot_id}/baseline", headers=admin_headers(), json={"reason": "E2E baseline"})).status_code == 200

        renamed = fixture("glpi-agent-hostname-changed.json")
        renamed_response = await client.post("/internal/inventories", headers=ingest_headers(uuid4().hex), json=renamed)
        assert renamed_response.status_code == 202
        changes = (await client.get(f"/admin/changes?endpoint_id={endpoint_id}", headers=admin_headers())).json()
        assert [item["type"] for item in changes].count("HOSTNAME_CHANGED") == 1
        renamed_snapshot_id = renamed_response.json()["snapshot_id"]
        await client.post(f"/admin/snapshots/{renamed_snapshot_id}/baseline", headers=admin_headers(), json={"reason": "Hostname acknowledged"})

        removed = fixture("glpi-agent-hardware-ram-removed.json")
        removed["content"]["hardware"]["name"] = "fixture-pc-renamed"
        removed_response = await client.post("/internal/inventories", headers=ingest_headers(uuid4().hex), json=removed)
        assert removed_response.status_code == 202
        changes = (await client.get(f"/admin/changes?endpoint_id={endpoint_id}", headers=admin_headers())).json()
        removals = [item for item in changes if item["type"] == "COMPONENT_REMOVED" and item["component_type"] == "RAM"]
        assert len(removals) == 1
        incidents = (await client.get(f"/admin/incidents?endpoint_id={endpoint_id}", headers=admin_headers())).json()
        removal_incidents = [item for item in incidents if item["change_event_id"] == removals[0]["id"]]
        assert len(removal_incidents) == 1

        identical_response = await client.post("/internal/inventories", headers=ingest_headers(uuid4().hex), json=removed)
        assert identical_response.status_code == 202
        changes_after_repeat = (await client.get(f"/admin/changes?endpoint_id={endpoint_id}", headers=admin_headers())).json()
        assert len(changes_after_repeat) == len(changes)

        incident_id = removal_incidents[0]["id"]
        assert (await client.post(f"/admin/incidents/{incident_id}/decision", headers=admin_headers(), json={
            "classification": "REQUIRES_INVESTIGATION", "actor": "pytest", "comment": "Review",
        })).status_code == 200
        assert (await client.post(f"/admin/incidents/{incident_id}/resolve", headers=admin_headers(), json={
            "classification": "AUTHORIZED_CHANGE", "actor": "pytest", "comment": "Approved",
        })).status_code == 200
        await client.post(f"/admin/snapshots/{removed_response.json()['snapshot_id']}/baseline", headers=admin_headers(), json={"reason": "Approved RAM state"})

        replaced = fixture("glpi-agent-hardware-ssd-replaced.json")
        replaced["content"]["hardware"]["name"] = "fixture-pc-renamed"
        replaced["content"]["memories"] = deepcopy(removed["content"]["memories"])
        assert (await client.post("/internal/inventories", headers=ingest_headers(uuid4().hex), json=replaced)).status_code == 202
        changes = (await client.get(f"/admin/changes?endpoint_id={endpoint_id}", headers=admin_headers())).json()
        replacements = [item for item in changes if item["type"] == "COMPONENT_REPLACED" and item["component_type"] == "STORAGE"]
        assert len(replacements) == 1

        partial = fixture("glpi-agent-partial-software-sanitized.json")
        assert (await client.post("/internal/inventories", headers=ingest_headers(uuid4().hex, "PARTIAL"), json=partial)).status_code == 202
        changes_after_partial = (await client.get(f"/admin/changes?endpoint_id={endpoint_id}", headers=admin_headers())).json()
        assert len(changes_after_partial) == len(changes)

        asset = (await client.get(f"/admin/assets/{asset_id}", headers=admin_headers())).json()
        history_types = {entry["type"] for entry in asset["history"]}
        assert {"ASSET_CREATED", "ENDPOINT_LINKED", "BASELINE_ACCEPTED", "HARDWARE_CHANGE_DETECTED", "INCIDENT_RESOLVED"} <= history_types

        user_response = await client.post("/admin/users", headers=admin_headers(), json={
            "username": "e2e-viewer", "password": "fixture-password-123", "role": "VIEWER",
        })
        assert user_response.status_code == 201
        login = await client.post("/auth/login", json={
            "username": "e2e-viewer", "password": "fixture-password-123",
        })
        assert login.status_code == 200
        viewer_headers = {"X-AssetGuard-Admin-Token": login.json()["access_token"]}
        assert (await client.get("/admin/assets", headers=viewer_headers)).status_code == 200
        assert (await client.post("/admin/assets", headers=viewer_headers, json={
            "inventory_number": "DENIED", "name": "Denied", "asset_type": "Other",
        })).status_code == 401
