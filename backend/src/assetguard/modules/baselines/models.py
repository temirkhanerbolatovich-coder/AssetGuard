from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from assetguard.modules.inventory.models import Base

class BaselineRecord(Base):
    __tablename__ = "baselines"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    managed_endpoint_id: Mapped[UUID] = mapped_column(ForeignKey("managed_endpoints.id"))
    hardware_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("hardware_snapshots.id"))
    status: Mapped[str] = mapped_column(String(16)); accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True)); superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True)); reason: Mapped[str | None] = mapped_column(Text)
