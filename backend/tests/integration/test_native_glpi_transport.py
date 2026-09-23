from __future__ import annotations

import asyncio
import base64

import httpx

from assetguard.app import app
from assetguard.infrastructure.config import get_settings

PROLOG = b"""<?xml version='1.0' encoding='UTF-8'?>
<REQUEST><DEVICEID>native-fixture-pc</DEVICEID><QUERY>PROLOG</QUERY></REQUEST>"""

INVENTORY = b"""<?xml version='1.0' encoding='UTF-8'?>
<REQUEST><CONTENT>
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


def test_native_glpi_agent_prolog_and_inventory() -> None:
    asyncio.run(_exercise_native_transport())


async def _exercise_native_transport() -> None:
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

        first = await client.post("/glpi-agent", headers=native, content=INVENTORY)
        duplicate = await client.post("/glpi-agent", headers=native, content=INVENTORY)
        assert first.status_code == duplicate.status_code == 200

        inventories = (await client.get("/admin/inventories", headers=admin)).json()
        native_rows = [item for item in inventories if item["schema_version"] == "glpi-agent-legacy-xml-v1"]
        assert len(native_rows) == 1
        assert native_rows[0]["processing_status"] == "PROCESSED"
        endpoints = (await client.get("/admin/endpoints", headers=admin)).json()
        native_endpoints = [item for item in endpoints if item["source_agent_id"] == "native-fixture-pc"]
        assert len(native_endpoints) == 1
