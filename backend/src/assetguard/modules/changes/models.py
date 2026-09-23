from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from assetguard.modules.inventory.models import Base

class ChangeEventRecord(Base):
    __tablename__ = "change_events"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    managed_endpoint_id: Mapped[UUID] = mapped_column(ForeignKey("managed_endpoints.id")); baseline_id: Mapped[UUID] = mapped_column(ForeignKey("baselines.id"))
    baseline_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("hardware_snapshots.id")); current_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("hardware_snapshots.id"))
    component_type: Mapped[str] = mapped_column(String(32)); previous_observation_id: Mapped[UUID | None] = mapped_column(ForeignKey("component_observations.id")); current_observation_id: Mapped[UUID | None] = mapped_column(ForeignKey("component_observations.id"))
    event_type: Mapped[str] = mapped_column(String(32)); confidence: Mapped[str] = mapped_column(String(16)); severity: Mapped[str] = mapped_column(String(16)); status: Mapped[str] = mapped_column(String(16))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB); detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True)); detector_version: Mapped[str] = mapped_column(String(32)); dedup_key: Mapped[str] = mapped_column(String(64))
