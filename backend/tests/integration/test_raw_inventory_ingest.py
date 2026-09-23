import asyncio
import json
from pathlib import Path

import httpx

from assetguard.app import app
from assetguard.infrastructure.config import get_settings


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "glpi-agent-full-sanitized.json"
IDEMPOTENCY_KEY = "integration-sanitized-glpi-agent-v1"


def test_raw_inventory_gateway_is_authenticated_and_idempotent() -> None:
    async def exercise_gateway() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        fixture_payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        headers = {
            "X-AssetGuard-Ingest-Token": get_settings().inventory_shared_secret,
            "X-AssetGuard-Idempotency-Key": IDEMPOTENCY_KEY,
            "X-AssetGuard-Source": "GLPI_AGENT",
            "X-AssetGuard-Source-Version": "1.19",
            "X-AssetGuard-Schema-Version": "phase0-fixture",
            "X-AssetGuard-Inventory-Type": "FULL",
        }
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            first = await client.post("/internal/inventories", headers=headers, json=fixture_payload)
            duplicate = await client.post(
                "/internal/inventories", headers=headers, json=fixture_payload
            )
            conflicting = await client.post(
                "/internal/inventories",
                headers=headers,
                json={"action": "different-payload"},
            )
        return first, duplicate, conflicting

    first, duplicate, conflicting = asyncio.run(exercise_gateway())

    assert first.status_code in (200, 202)
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert conflicting.status_code == 409

