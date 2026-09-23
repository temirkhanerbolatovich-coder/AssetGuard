"""Source boundary contracts kept separate from the canonical inventory model."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Protocol
from xml.etree import ElementTree

from assetguard.modules.inventory.service import RawInventoryIngestCommand


@dataclass(frozen=True, slots=True)
class InventorySourceMetadata:
    source: str
    source_version: str | None
    schema_version: str | None
    inventory_type: str
    idempotency_key: str


class InventorySourceAdapter(Protocol):
    def to_ingest_command(
        self, payload: dict[str, Any], metadata: InventorySourceMetadata,
    ) -> RawInventoryIngestCommand: ...


class TrustedJsonBridgeAdapter:
    """Current explicit bridge; it does not pretend to implement GLPI's native protocol."""

    def to_ingest_command(
        self, payload: dict[str, Any], metadata: InventorySourceMetadata,
    ) -> RawInventoryIngestCommand:
        return RawInventoryIngestCommand(
            source=metadata.source,
            source_version=metadata.source_version,
            schema_version=metadata.schema_version,
            inventory_type=metadata.inventory_type,
            idempotency_key=metadata.idempotency_key,
            payload=payload,
        )


@dataclass(frozen=True, slots=True)
class GlpiLegacyRequest:
    query: str
    device_id: str
    payload: dict[str, Any] | None
    source_version: str | None
    inventory_type: str
    idempotency_key: str


class DirectGlpiAgentAdapter(TrustedJsonBridgeAdapter):
    """Parse the observed GLPI Agent 1.19 legacy XML protocol without GLPI IDs."""

    _singular_sections = {"BIOS", "HARDWARE", "OPERATINGSYSTEM"}

    def parse(self, raw_xml: bytes) -> GlpiLegacyRequest:
        upper_prefix = raw_xml[:4096].upper()
        if b"<!DOCTYPE" in upper_prefix or b"<!ENTITY" in upper_prefix:
            raise ValueError("DTD and entity declarations are not accepted.")
        try:
            root = ElementTree.fromstring(raw_xml)
        except ElementTree.ParseError as error:
            raise ValueError("GLPI Agent request must contain valid XML.") from error
        if root.tag != "REQUEST":
            raise ValueError("GLPI Agent XML root must be REQUEST.")
        query = (root.findtext("QUERY") or "").strip().upper()
        device_id = (root.findtext("DEVICEID") or "").strip()
        if query not in {"PROLOG", "INVENTORY"} or not device_id:
            raise ValueError("GLPI Agent request must contain PROLOG/INVENTORY and DEVICEID.")
        digest = sha256(raw_xml).hexdigest()
        if query == "PROLOG":
            return GlpiLegacyRequest(query, device_id, None, None, "PARTIAL", f"glpi-prolog:{digest}")

        content_node = root.find("CONTENT")
        if content_node is None:
            raise ValueError("GLPI INVENTORY request does not contain CONTENT.")
        content: dict[str, Any] = {}
        grouped: dict[str, list[Any]] = {}
        for section in content_node:
            if len(section):
                value = {child.tag.lower(): (child.text or "").strip() for child in section}
            else:
                value = (section.text or "").strip()
            grouped.setdefault(section.tag, []).append(value)
        for name, values in grouped.items():
            key = name.lower()
            content[key] = values[0] if name in self._singular_sections or name == "VERSIONCLIENT" else values
        source_version = content.get("versionclient") if isinstance(content.get("versionclient"), str) else None
        complete = all(isinstance(content.get(category), list) for category in ("memories", "storages"))
        canonical = {
            "action": "inventory",
            "deviceid": device_id,
            "itemtype": "Computer",
            "content": content,
            "_transport": {
                "protocol": "glpi-agent-legacy-xml",
                "raw_xml": raw_xml.decode("utf-8", errors="replace"),
                "raw_sha256": digest,
            },
        }
        return GlpiLegacyRequest(
            query, device_id, canonical, source_version,
            "FULL" if complete else "PARTIAL",
            f"glpi-inventory:{device_id}:{digest}",
        )


def get_source_adapter() -> InventorySourceAdapter:
    return TrustedJsonBridgeAdapter()
