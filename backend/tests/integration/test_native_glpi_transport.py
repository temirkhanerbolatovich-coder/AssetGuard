from __future__ import annotations

import asyncio
import base64
from xml.etree import ElementTree

import httpx
import pytest

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.interfaces.http.admin_assets import _installer_version
from assetguard.modules.inventory.adapters import DirectGlpiAgentAdapter

PROLOG = b"""<?xml version='1.0' encoding='UTF-8'?>
<REQUEST><DEVICEID>native-fixture-pc</DEVICEID><QUERY>PROLOG</QUERY></REQUEST>"""

INVENTORY = b"""<?xml version='1.0' encoding='UTF-8'?>
<REQUEST><CONTENT>
  <ACCOUNTINFO><KEYNAME>TAG</KEYNAME><KEYVALUE>assetguard-installer-0.1.8</KEYVALUE></ACCOUNTINFO>
  <BIOS><BSERIAL>NATIVE-BIOS</BSERIAL></BIOS>
  <HARDWARE><UUID>NATIVE-UUID</UUID><NAME>native-fixture-pc</NAME></HARDWARE>
  <CPUS><NAME>Native CPU</NAME></CPUS>
  <MEMORIES><SERIALNUMBER>NATIVE-RAM-A</SERIALNUMBER><NUMSLOTS>DIMM 0</NUMSLOTS><CAPACITY>8192</CAPACITY></MEMORIES>
  <MEMORIES><SERIALNUMBER>NATIVE-RAM-B</SERIALNUMBER><NUMSLOTS>DIMM 1</NUMSLOTS><CAPACITY>8192</CAPACITY></MEMORIES>
  <STORAGES><SERIAL>NATIVE-SSD</SERIAL><MODEL>Native SSD</MODEL><DISKSIZE>512000</DISKSIZE></STORAGES>
  <MONITORS><SERIAL>NATIVE-MONITOR</SERIAL><CAPTION>Native Monitor</CAPTION></MONITORS>
  <NETWORKS><MACADDR>02:00:00:00:00:11</MACADDR><DESCRIPTION>Native NIC</DESCRIPTION></NETWORKS>
  <VERSIONCLIENT>1.19</VERSIONCLIENT>
</CONTENT><DEVICEID>native-fixture-pc</DEVICEID><QUERY>INVENTORY</QUERY></REQUEST>"""


@pytest.mark.parametrize("agent_version", ["1.19", "1.20"])
def test_native_glpi_agent_prolog_and_inventory(agent_version: str) -> None:
    asyncio.run(_exercise_native_transport(agent_version))


def test_per_agent_credential_binds_and_can_be_revoked() -> None:
    asyncio.run(_exercise_per_agent_credential())


async def _exercise_native_transport(agent_version: str) -> None:
    credentials = base64.b64encode(
        f"assetguard:{get_settings().inventory_shared_secret}".encode()
    ).decode()
    native = {"Authorization": f"Basic {credentials}", "Content-Type": "application/xml"}
    admin = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        assert (await client.post("/glpi-agent", content=PROLOG)).status_code == 401
        prolog = await client.post("/glpi-agent", headers=native, content=PROLOG)
        assert prolog.status_code == 200
        assert b"<RESPONSE>SEND</RESPONSE>" in prolog.content
        hours = float(ElementTree.fromstring(prolog.content).findtext("PROLOG_FREQ"))
        assert hours * 3600 == pytest.approx(get_settings().glpi_prolog_interval_seconds)

        inventory = INVENTORY.replace(b"1.19", agent_version.encode("ascii"))
        parsed = DirectGlpiAgentAdapter().parse(inventory)
        assert _installer_version(parsed.payload["content"]) == "0.1.8"
        first = await client.post("/glpi-agent", headers=native, content=inventory)
        duplicate = await client.post("/glpi-agent", headers=native, content=inventory)
        assert first.status_code == duplicate.status_code == 200

        inventories = (await client.get("/admin/inventories", headers=admin)).json()
        native_rows = [item for item in inventories if item["schema_version"] == "glpi-agent-legacy-xml-v1"]
        assert len(native_rows) == 1
        assert native_rows[0]["processing_status"] == "PROCESSED"
        assert native_rows[0]["source_version"] == agent_version
        endpoints = (await client.get("/admin/endpoints", headers=admin)).json()
        native_endpoints = [item for item in endpoints if item["source_agent_id"] == "native-fixture-pc"]
        assert len(native_endpoints) == 1


async def _exercise_per_agent_credential() -> None:
    admin = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
    transport = httpx.ASGITransport(app=app)
    unique_inventory = INVENTORY.replace(b"native-fixture-pc", b"credential-fixture-pc").replace(b"NATIVE-UUID", b"CREDENTIAL-UUID")
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post("/admin/agent-credentials", headers=admin)
        assert created.status_code == 201
        issued = created.json()
        assert issued["username"].startswith("ag-")
        assert len(issued["secret"]) >= 32
        encoded = base64.b64encode(f"{issued['username']}:{issued['secret']}".encode()).decode()
        headers = {"Authorization": f"Basic {encoded}", "Content-Type": "application/xml"}
        assert (await client.post("/glpi-agent", headers=headers, content=unique_inventory)).status_code == 200
        credentials = (await client.get("/admin/agent-credentials", headers=admin)).json()
        record = next(item for item in credentials if item["id"] == issued["id"])
        assert record["endpoint_id"] is not None
        assert "secret" not in record
        assert (await client.post(f"/admin/agent-credentials/{issued['id']}/revoke", headers=admin)).status_code == 200
        assert (await client.post("/glpi-agent", headers=headers, content=PROLOG)).status_code == 401
