"""Source boundary contracts kept separate from the canonical inventory model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

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


def get_source_adapter() -> InventorySourceAdapter:
    return TrustedJsonBridgeAdapter()
