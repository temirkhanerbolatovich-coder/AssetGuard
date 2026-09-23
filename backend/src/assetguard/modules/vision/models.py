from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from assetguard.modules.inventory.models import Base


class VisionRoomRecord(Base):
    __tablename__ = "vision_rooms"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class VisionScanRecord(Base):
    __tablename__ = "vision_scans"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    room_id: Mapped[UUID] = mapped_column(ForeignKey("vision_rooms.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    original_image_path: Mapped[str] = mapped_column(Text)
    annotated_image_path: Mapped[str] = mapped_column(Text)
    counts: Mapped[dict[str, int]] = mapped_column(JSONB)
    comparison: Mapped[dict[str, Any]] = mapped_column(JSONB)
    model_id: Mapped[str] = mapped_column(String(255))
    confidence_threshold: Mapped[float] = mapped_column(Float)


class VisionDetectionRecord(Base):
    __tablename__ = "vision_detections"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    scan_id: Mapped[UUID] = mapped_column(ForeignKey("vision_scans.id"))
    class_name: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    bbox: Mapped[dict[str, float]] = mapped_column(JSONB)


class VisionBaselineRecord(Base):
    __tablename__ = "vision_baselines"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    room_id: Mapped[UUID] = mapped_column(ForeignKey("vision_rooms.id"), unique=True)
    source_scan_id: Mapped[UUID] = mapped_column(ForeignKey("vision_scans.id"))
    counts: Mapped[dict[str, int]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
