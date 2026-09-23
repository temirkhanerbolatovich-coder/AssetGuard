"""Append-only history helpers shared by MVP workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from assetguard.modules.incidents.models import AssetHistoryEntryRecord, EndpointHistoryEntryRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord


def append_history(
    session: Session, *, endpoint: ManagedEndpointRecord, event_type: str,
    related_entity_type: str, related_entity_id: UUID, message: str,
    metadata: dict[str, Any] | None = None, occurred_at: datetime | None = None,
) -> None:
    when = occurred_at or datetime.now(UTC)
    details = metadata or {}
    session.add(EndpointHistoryEntryRecord(
        managed_endpoint_id=endpoint.id, event_type=event_type, occurred_at=when,
        related_entity_type=related_entity_type, related_entity_id=related_entity_id,
        message=message, metadata_json=details,
    ))
    if endpoint.asset_id:
        session.add(AssetHistoryEntryRecord(
            asset_id=endpoint.asset_id, managed_endpoint_id=endpoint.id,
            event_type=event_type, occurred_at=when,
            related_entity_type=related_entity_type, related_entity_id=related_entity_id,
            message=message, metadata_json=details,
        ))


def append_asset_history(
    session: Session, *, asset_id: UUID, event_type: str,
    related_entity_type: str, related_entity_id: UUID, message: str,
    endpoint_id: UUID | None = None, metadata: dict[str, Any] | None = None,
) -> None:
    session.add(AssetHistoryEntryRecord(
        asset_id=asset_id, managed_endpoint_id=endpoint_id,
        event_type=event_type, occurred_at=datetime.now(UTC),
        related_entity_type=related_entity_type, related_entity_id=related_entity_id,
        message=message, metadata_json=metadata or {},
    ))
