from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from assetguard.modules.inventory.models import Base

class OrganizationRecord(Base):
    __tablename__="organizations"
    id: Mapped[UUID]=mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4); name: Mapped[str]=mapped_column(String(255)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
class AssetRecord(Base):
    __tablename__="assets"
    id: Mapped[UUID]=mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4); organization_id: Mapped[UUID]=mapped_column(ForeignKey("organizations.id")); inventory_number: Mapped[str]=mapped_column(String(128)); name: Mapped[str]=mapped_column(String(255)); asset_type: Mapped[str]=mapped_column(String(16)); status: Mapped[str]=mapped_column(String(32)); room: Mapped[str|None]=mapped_column(String(255)); notes: Mapped[str|None]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
