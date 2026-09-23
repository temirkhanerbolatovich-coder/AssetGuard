"""Persistence mappings for normalized endpoint snapshots."""
from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from assetguard.modules.inventory.models import Base

class ManagedEndpointRecord(Base):
    __tablename__ = "managed_endpoints"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(64)); source_agent_id: Mapped[str | None] = mapped_column(String(255)); asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id"))
    hostname: Mapped[str | None] = mapped_column(String(255)); last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32)); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class EndpointIdentifierRecord(Base):
    __tablename__ = "endpoint_identifiers"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    managed_endpoint_id: Mapped[UUID] = mapped_column(ForeignKey("managed_endpoints.id")); identifier_type: Mapped[str] = mapped_column(String(32))
    raw_value: Mapped[str] = mapped_column(String(512)); normalized_value: Mapped[str] = mapped_column(String(512)); confidence: Mapped[str] = mapped_column(String(16))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)); last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)); is_active: Mapped[bool] = mapped_column(Boolean)

class HardwareSnapshotRecord(Base):
    __tablename__ = "hardware_snapshots"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    managed_endpoint_id: Mapped[UUID] = mapped_column(ForeignKey("managed_endpoints.id")); raw_inventory_id: Mapped[UUID] = mapped_column(ForeignKey("raw_inventories.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    snapshot_type: Mapped[str] = mapped_column(String(16)); completeness: Mapped[dict[str, Any]] = mapped_column(JSONB); normalizer_version: Mapped[str] = mapped_column(String(32))

class ComponentIdentityRecord(Base):
    __tablename__ = "component_identities"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    component_type: Mapped[str] = mapped_column(String(32)); canonical_serial: Mapped[str | None] = mapped_column(String(512))
    manufacturer: Mapped[str | None] = mapped_column(String(255)); model: Mapped[str | None] = mapped_column(String(512)); part_number: Mapped[str | None] = mapped_column(String(255))
    identity_confidence: Mapped[str] = mapped_column(String(16)); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class ComponentObservationRecord(Base):
    __tablename__ = "component_observations"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    hardware_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("hardware_snapshots.id")); component_type: Mapped[str] = mapped_column(String(32))
    component_identity_id: Mapped[UUID | None] = mapped_column(ForeignKey("component_identities.id")); manufacturer: Mapped[str | None] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(512)); serial_number: Mapped[str | None] = mapped_column(String(512)); part_number: Mapped[str | None] = mapped_column(String(255))
    capacity: Mapped[int | None] = mapped_column(BigInteger); slot: Mapped[str | None] = mapped_column(String(255)); source_key: Mapped[str | None] = mapped_column(String(512))
    confidence: Mapped[str] = mapped_column(String(16)); raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB)
