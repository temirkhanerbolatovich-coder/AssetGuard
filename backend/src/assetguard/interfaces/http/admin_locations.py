from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.admin_assets import require_admin, require_viewer
from assetguard.modules.assets.models import AssetRecord, BuildingRecord, FloorRecord, OrganizationRecord, RoomRecord
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.snapshots.models import ManagedEndpointRecord

router = APIRouter(prefix="/admin/locations", tags=["locations"])


class BuildingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    responsible_name: str | None = Field(default=None, max_length=255)
    responsible_contact: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class FloorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    responsible_name: str | None = Field(default=None, max_length=255)
    responsible_contact: str | None = Field(default=None, max_length=255)


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    purpose: str | None = Field(default=None, max_length=255)
    responsible_name: str | None = Field(default=None, max_length=255)
    responsible_contact: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class RoomUpdate(BaseModel):
    purpose: str | None = Field(default=None, max_length=255)
    responsible_name: str | None = Field(default=None, max_length=255)
    responsible_contact: str | None = Field(default=None, max_length=255)
    notes: str | None = None


def _clean(value: str | None) -> str | None:
    return " ".join(value.split()) if value and value.strip() else None


def _organization(session: Session, principal: AuthPrincipal) -> OrganizationRecord:
    if principal.organization_id:
        organization = session.get(OrganizationRecord, principal.organization_id)
    else:
        organization = session.scalar(select(OrganizationRecord).order_by(OrganizationRecord.created_at))
    if not organization:
        organization = OrganizationRecord(name="Default Organization", created_at=datetime.now(UTC))
        session.add(organization); session.flush()
    return organization


def _building(session: Session, building_id: UUID, principal: AuthPrincipal) -> BuildingRecord:
    building = session.get(BuildingRecord, building_id)
    if not building or (principal.organization_id and building.organization_id != principal.organization_id):
        raise HTTPException(404, "Building was not found.")
    return building


def _floor(session: Session, floor_id: UUID, principal: AuthPrincipal) -> FloorRecord:
    floor = session.get(FloorRecord, floor_id)
    if not floor:
        raise HTTPException(404, "Floor was not found.")
    _building(session, floor.building_id, principal)
    return floor


def _room(session: Session, room_id: UUID, principal: AuthPrincipal) -> RoomRecord:
    room = session.get(RoomRecord, room_id)
    if not room:
        raise HTTPException(404, "Room was not found.")
    _floor(session, room.floor_id, principal)
    return room


def _room_view(session: Session, room: RoomRecord) -> dict:
    assets = list(session.scalars(select(AssetRecord).where(AssetRecord.room_id == room.id).order_by(AssetRecord.inventory_number)))
    endpoint_ids = [asset.id for asset in assets]
    endpoints = list(session.scalars(select(ManagedEndpointRecord).where(ManagedEndpointRecord.asset_id.in_(endpoint_ids)))) if endpoint_ids else []
    return {
        "id": str(room.id), "name": room.name, "purpose": room.purpose,
        "responsible_name": room.responsible_name, "responsible_contact": room.responsible_contact, "notes": room.notes,
        "asset_count": len(assets), "endpoint_count": len(endpoints),
        "online_count": sum(1 for item in endpoints if item.status == "ONLINE"),
    }


@router.get("/tree")
def location_tree(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    query = select(BuildingRecord).order_by(BuildingRecord.name)
    if principal.organization_id:
        query = query.where(BuildingRecord.organization_id == principal.organization_id)
    result = []
    for building in session.scalars(query):
        floors = []
        for floor in session.scalars(select(FloorRecord).where(FloorRecord.building_id == building.id).order_by(FloorRecord.name)):
            floors.append({"id": str(floor.id), "name": floor.name, "responsible_name": floor.responsible_name, "responsible_contact": floor.responsible_contact, "rooms": [_room_view(session, room) for room in session.scalars(select(RoomRecord).where(RoomRecord.floor_id == floor.id).order_by(RoomRecord.name))]})
        result.append({"id": str(building.id), "name": building.name, "responsible_name": building.responsible_name, "responsible_contact": building.responsible_contact, "notes": building.notes, "floors": floors})
    return result


@router.post("/buildings", status_code=status.HTTP_201_CREATED)
def create_building(body: BuildingCreate, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    organization = _organization(session, principal); name = _clean(body.name)
    if session.scalar(select(BuildingRecord).where(BuildingRecord.organization_id == organization.id, BuildingRecord.name == name)):
        raise HTTPException(409, "A building with this name already exists.")
    building = BuildingRecord(organization_id=organization.id, name=name or "", responsible_name=_clean(body.responsible_name), responsible_contact=_clean(body.responsible_contact), notes=_clean(body.notes), created_at=datetime.now(UTC))
    session.add(building); session.commit(); session.refresh(building)
    return {"id": str(building.id), "name": building.name}


@router.post("/buildings/{building_id}/floors", status_code=status.HTTP_201_CREATED)
def create_floor(building_id: UUID, body: FloorCreate, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    building = _building(session, building_id, principal); name = _clean(body.name)
    if session.scalar(select(FloorRecord).where(FloorRecord.building_id == building.id, FloorRecord.name == name)):
        raise HTTPException(409, "A floor with this name already exists in this building.")
    floor = FloorRecord(building_id=building.id, name=name or "", responsible_name=_clean(body.responsible_name), responsible_contact=_clean(body.responsible_contact), created_at=datetime.now(UTC))
    session.add(floor); session.commit(); session.refresh(floor)
    return {"id": str(floor.id), "name": floor.name}


@router.post("/floors/{floor_id}/rooms", status_code=status.HTTP_201_CREATED)
def create_room(floor_id: UUID, body: RoomCreate, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    floor = _floor(session, floor_id, principal); name = _clean(body.name)
    if session.scalar(select(RoomRecord).where(RoomRecord.floor_id == floor.id, RoomRecord.name == name)):
        raise HTTPException(409, "A room with this name already exists on this floor.")
    room = RoomRecord(floor_id=floor.id, name=name or "", purpose=_clean(body.purpose), responsible_name=_clean(body.responsible_name), responsible_contact=_clean(body.responsible_contact), notes=_clean(body.notes), created_at=datetime.now(UTC))
    session.add(room); session.commit(); session.refresh(room)
    return _room_view(session, room)


@router.patch("/rooms/{room_id}")
def update_room(room_id: UUID, body: RoomUpdate, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    room = _room(session, room_id, principal)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(room, field, _clean(value))
    session.commit(); session.refresh(room)
    return _room_view(session, room)


@router.get("/rooms/{room_id}/report")
def room_report(room_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    room = _room(session, room_id, principal); floor = session.get(FloorRecord, room.floor_id); building = session.get(BuildingRecord, floor.building_id) if floor else None
    assets = list(session.scalars(select(AssetRecord).where(AssetRecord.room_id == room.id).order_by(AssetRecord.inventory_number)))
    return {"room": _room_view(session, room), "path": {"building": building.name if building else None, "floor": floor.name if floor else None}, "assets": [{"id": str(asset.id), "inventory_number": asset.inventory_number, "name": asset.name, "status": asset.status, "asset_type": asset.asset_type} for asset in assets]}
