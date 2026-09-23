"""Persistence mapping for immutable raw inventory evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for AssetGuard SQLAlchemy mappings."""


class RawInventoryRecord(Base):
    """Raw JSON evidence; its evidence fields are protected by a DB trigger."""

    __tablename__ = "raw_inventories"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    managed_endpoint_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    inventory_type: Mapped[str] = mapped_column(String(16), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(16), nullable=False)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingest_idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True
    )

