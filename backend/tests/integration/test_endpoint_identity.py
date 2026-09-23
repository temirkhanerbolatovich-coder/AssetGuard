from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import httpx

from assetguard.app import app
from assetguard.infrastructure.config import get_settings

FIXTURE = Path(__file__).parents[1] / "fixtures" / "glpi-agent-minimal-sanitized.json"


def headers() -> dict[str, str]:
    return {
        "X-AssetGuard-Ingest-Token": get_settings().inventory_shared_secret,
        "X-AssetGuard-Idempotency-Key": uuid4().hex,
        "X-AssetGuard-Source": "GLPI_AGENT",
        "X-AssetGuard-Source-Version": "1.19",
        "X-AssetGuard-Schema-Version": "identity-test-v1",
        "X-AssetGuard-Inventory-Type": "FULL",
    }


def test_identity_change_and_cross_endpoint_conflict_are_explicit() -> None:
    asyncio.run(_exercise_identity_rules())


async def _exercise_identity_rules() -> None:
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source["content"]["bios"]["bserial"] = "BIOS-A"
    admin = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post("/internal/inventories", headers=headers(), json=source)
        assert first.status_code == 202, first.text
        first_snapshot = first.json()["snapshot_id"]
        snapshot = (await client.get(f"/admin/snapshots/{first_snapshot}", headers=admin)).json()
        endpoint_id = snapshot["endpoint_id"]
        assert (await client.post(
            f"/admin/snapshots/{first_snapshot}/baseline", headers=admin, json={"reason": "identity test"},
        )).status_code == 200

        changed = deepcopy(source)
        changed["content"]["bios"]["bserial"] = "BIOS-B"
        changed_response = await client.post("/internal/inventories", headers=headers(), json=changed)
        assert changed_response.status_code == 202, changed_response.text
        changes = (await client.get(f"/admin/changes?endpoint_id={endpoint_id}", headers=admin)).json()
        identity_events = [item for item in changes if item["type"] == "DEVICE_IDENTITY_CHANGED"]
        assert len(identity_events) == 1
        assert identity_events[0]["evidence"]["previous"]["value"] == "BIOS-A"
        assert identity_events[0]["evidence"]["current"]["value"] == "BIOS-B"

        other = deepcopy(source)
        other["deviceid"] = "fixture-device-other"
        other["content"]["hardware"]["uuid"] = "fixture-smbios-other"
        other["content"]["bios"]["bserial"] = "BIOS-OTHER"
        other["content"]["networks"][0]["macaddr"] = "02:00:00:00:00:02"
        assert (await client.post("/internal/inventories", headers=headers(), json=other)).status_code == 202
        endpoint_rows = (await client.get("/admin/endpoints", headers=admin)).json()
        assert len(endpoint_rows) >= 2, endpoint_rows

        conflict = deepcopy(changed)
        conflict["deviceid"] = other["deviceid"]
        conflict_response = await client.post("/internal/inventories", headers=headers(), json=conflict)
        assert conflict_response.status_code == 422
        assert "multiple managed endpoints" in conflict_response.json()["detail"]
