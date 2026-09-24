from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from assetguard.modules.inventory.models import Base

class OrganizationRecord(Base):
    __tablename__="organizations"
    id: Mapped[UUID]=mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4); name: Mapped[str]=mapped_column(String(255)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
class BuildingRecord(Base):
    __tablename__="location_buildings"
    __table_args__=(UniqueConstraint("organization_id", "name", name="uq_location_building_org_name"),)
    id: Mapped[UUID]=mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4); organization_id: Mapped[UUID]=mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT")); name: Mapped[str]=mapped_column(String(255)); responsible_name: Mapped[str|None]=mapped_column(String(255)); responsible_contact: Mapped[str|None]=mapped_column(String(255)); notes: Mapped[str|None]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
class FloorRecord(Base):
    __tablename__="location_floors"
    __table_args__=(UniqueConstraint("building_id", "name", name="uq_location_floor_building_name"),)
    id: Mapped[UUID]=mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4); building_id: Mapped[UUID]=mapped_column(ForeignKey("location_buildings.id", ondelete="RESTRICT")); name: Mapped[str]=mapped_column(String(64)); responsible_name: Mapped[str|None]=mapped_column(String(255)); responsible_contact: Mapped[str|None]=mapped_column(String(255)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
class RoomRecord(Base):
    __tablename__="location_rooms"
    __table_args__=(UniqueConstraint("floor_id", "name", name="uq_location_room_floor_name"),)
    id: Mapped[UUID]=mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4); floor_id: Mapped[UUID]=mapped_column(ForeignKey("location_floors.id", ondelete="RESTRICT")); name: Mapped[str]=mapped_column(String(255)); purpose: Mapped[str|None]=mapped_column(String(255)); responsible_name: Mapped[str|None]=mapped_column(String(255)); responsible_contact: Mapped[str|None]=mapped_column(String(255)); notes: Mapped[str|None]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
class AssetRecord(Base):
    __tablename__="assets"
    id: Mapped[UUID]=mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4); organization_id: Mapped[UUID]=mapped_column(ForeignKey("organizations.id")); room_id: Mapped[UUID|None]=mapped_column(ForeignKey("location_rooms.id", ondelete="RESTRICT"), nullable=True); inventory_number: Mapped[str]=mapped_column(String(128)); name: Mapped[str]=mapped_column(String(255)); asset_type: Mapped[str]=mapped_column(String(16)); status: Mapped[str]=mapped_column(String(32)); building: Mapped[str|None]=mapped_column(String(255)); floor: Mapped[str|None]=mapped_column(String(64)); room: Mapped[str|None]=mapped_column(String(255)); notes: Mapped[str|None]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
