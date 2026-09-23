from __future__ import annotations

import asyncio
import json
from io import BytesIO
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import httpx
from openpyxl import Workbook
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
        initial["content"]["assetguard_network"] = {
            "target": "1.1.1.1", "probes": 4, "replies": 4,
            "packet_loss_percent": 0, "average_latency_ms": 22.5,
            "measured_at": "2026-09-23T12:00:00Z",
        }
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
        location_update = await client.patch(f"/admin/assets/{asset_id}", headers=admin_headers(), json={
            "building": "Корпус А", "floor": "2", "room": "205",
        })
        assert location_update.status_code == 200
        assert location_update.json()["building"] == "Корпус А"
        assert location_update.json()["floor"] == "2"
        export = await client.get("/admin/assets/export.xlsx", headers=admin_headers())
        assert export.status_code == 200
        assert export.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        qr = await client.get(f"/admin/assets/{asset_id}/qr.svg?public_url=https://demo.trycloudflare.com", headers=admin_headers())
        assert qr.status_code == 200
        assert qr.headers["content-type"].startswith("image/svg+xml")
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["inventory_number", "name", "asset_type", "organization", "building", "floor", "room"])
        worksheet.append(["XLSX-001", "Imported workstation", "Desktop", "Imported Organization", "Корпус Б", "3", "301"])
        stream = BytesIO(); workbook.save(stream)
        imported = await client.post("/admin/assets/import.xlsx?apply=true", headers=admin_headers(), files={
            "file": ("assets.xlsx", stream.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        })
        assert imported.status_code == 200
        assert imported.json()["creates"] == 1
        assert (await client.post(f"/admin/endpoints/{endpoint_id}/asset/{asset_id}", headers=admin_headers())).status_code == 200
        asset_detail = await client.get(f"/admin/assets/{asset_id}", headers=admin_headers())
        assert asset_detail.json()["system"]["network_quality"]["average_latency_ms"] == 22.5
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
        incident_detail = (await client.get(f"/admin/incidents/{incident_id}", headers=admin_headers())).json()
        assert {item["actor"] for item in incident_detail["decisions"]} == {"bootstrap-admin"}
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
        assert asset["organization"] == "Default Organization"
        assert asset["endpoint"]["current_snapshot"]["type"] == "PARTIAL"
        assert asset["endpoint"]["hardware_summary"]["ram_bytes"] == 8 * 1024**3
        assert asset["endpoint"]["identifiers"]
        assert asset["latest_inventory"]["processing_status"] == "PROCESSED"
        assert asset["system"]["hardware"]["uuid"] == "fixture-smbios-uuid"
        assert any(component["type"] == "CPU" and "raw_data" in component for component in asset["current_hardware"])
        assert next(component for component in asset["current_hardware"] if component["type"] == "RAM")["capacity"] == 8 * 1024**3
        history_types = {entry["type"] for entry in asset["history"]}
        assert {"ASSET_CREATED", "ENDPOINT_LINKED", "BASELINE_ACCEPTED", "HARDWARE_CHANGE_DETECTED", "INCIDENT_RESOLVED", "INVENTORY_COMPLETED"} <= history_types

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
