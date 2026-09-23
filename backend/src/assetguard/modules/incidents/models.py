from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from assetguard.modules.inventory.models import Base


class IncidentRecord(Base):
    __tablename__ = "incidents"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    managed_endpoint_id: Mapped[UUID] = mapped_column(ForeignKey("managed_endpoints.id"))
    change_event_id: Mapped[UUID] = mapped_column(ForeignKey("change_events.id"))
    status: Mapped[str] = mapped_column(String(16))
    severity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IncidentDecisionRecord(Base):
    __tablename__ = "incident_decisions"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"))
    classification: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EndpointHistoryEntryRecord(Base):
    __tablename__ = "endpoint_history_entries"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    managed_endpoint_id: Mapped[UUID] = mapped_column(ForeignKey("managed_endpoints.id"))
    event_type: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    related_entity_type: Mapped[str] = mapped_column(String(64))
    related_entity_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    message: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB)


class AssetHistoryEntryRecord(Base):
    __tablename__ = "asset_history_entries"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"))
    managed_endpoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("managed_endpoints.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    related_entity_type: Mapped[str] = mapped_column(String(64))
    related_entity_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    message: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB)
