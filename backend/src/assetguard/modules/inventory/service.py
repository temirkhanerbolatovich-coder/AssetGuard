"""Application service for immutable raw inventory reception."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.modules.inventory.models import RawInventoryRecord
from assetguard.modules.inventory.raw_inventory import payload_sha256


class IdempotencyConflictError(ValueError):
    """A caller reused a key with a different payload."""


@dataclass(frozen=True, slots=True)
class RawInventoryIngestCommand:
    source: str
    source_version: str | None
    schema_version: str | None
    inventory_type: str
    idempotency_key: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RawInventoryIngestResult:
    raw_inventory: RawInventoryRecord
    duplicate: bool


def ingest_raw_inventory(
    session: Session, command: RawInventoryIngestCommand
) -> RawInventoryIngestResult:
    """Persist raw evidence once for a transport idempotency key."""
    payload_hash = payload_sha256(command.payload)
    existing = session.scalar(
        select(RawInventoryRecord).where(
            RawInventoryRecord.ingest_idempotency_key == command.idempotency_key
        )
    )
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise IdempotencyConflictError(
                "Idempotency key has already been used for a different payload."
            )
        return RawInventoryIngestResult(raw_inventory=existing, duplicate=True)

    record = RawInventoryRecord(
        source=command.source,
        source_version=command.source_version,
        schema_version=command.schema_version,
        received_at=datetime.now(UTC),
        payload_hash=payload_hash,
        payload=command.payload,
        inventory_type=command.inventory_type,
        processing_status="RECEIVED",
        ingest_idempotency_key=command.idempotency_key,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return RawInventoryIngestResult(raw_inventory=record, duplicate=False)
