from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.admin_assets import require_admin, require_viewer
from assetguard.modules.assets.models import AssetRecord, BuildingRecord, FloorRecord, OrganizationRecord, RoomRecord
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.identity.location_access import permitted_room_ids, require_room_access
from assetguard.modules.identity.models import LocationAccessRecord, UserRecord
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


class AccessGrant(BaseModel):
    user_id: UUID
    scope_type: Literal["BUILDING", "FLOOR", "ROOM"]
    scope_id: UUID
    permission: Literal["VIEWER", "EDITOR"]


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
    require_room_access(session, room.id, principal)
    return room


def _scope_organization(session: Session, scope_type: str, scope_id: UUID) -> UUID | None:
    if scope_type == "BUILDING":
        item = session.get(BuildingRecord, scope_id); return item.organization_id if item else None
    if scope_type == "FLOOR":
        floor = session.get(FloorRecord, scope_id); building = session.get(BuildingRecord, floor.building_id) if floor else None; return building.organization_id if building else None
    room = session.get(RoomRecord, scope_id); floor = session.get(FloorRecord, room.floor_id) if room else None; building = session.get(BuildingRecord, floor.building_id) if floor else None; return building.organization_id if building else None


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
    result = []; allowed_rooms = permitted_room_ids(session, principal)
    for building in session.scalars(query):
        floors = []
        for floor in session.scalars(select(FloorRecord).where(FloorRecord.building_id == building.id).order_by(FloorRecord.name)):
            rooms = [room for room in session.scalars(select(RoomRecord).where(RoomRecord.floor_id == floor.id).order_by(RoomRecord.name)) if allowed_rooms is None or room.id in allowed_rooms]
            if rooms: floors.append({"id": str(floor.id), "name": floor.name, "responsible_name": floor.responsible_name, "responsible_contact": floor.responsible_contact, "rooms": [_room_view(session, room) for room in rooms]})
        if floors: result.append({"id": str(building.id), "name": building.name, "responsible_name": building.responsible_name, "responsible_contact": building.responsible_contact, "notes": building.notes, "floors": floors})
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


@router.get("/access")
def list_access(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    query = select(LocationAccessRecord).order_by(LocationAccessRecord.created_at.desc())
    rows = []
    for item in session.scalars(query):
        user = session.get(UserRecord, item.user_id)
        if not user or (principal.organization_id and user.organization_id != principal.organization_id):
            continue
        rows.append({"id": str(item.id), "user_id": str(item.user_id), "username": user.username, "scope_type": item.scope_type, "scope_id": str(item.scope_id), "permission": item.permission})
    return rows


@router.post("/access", status_code=status.HTTP_201_CREATED)
def grant_access(body: AccessGrant, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    user = session.get(UserRecord, body.user_id); scope_organization = _scope_organization(session, body.scope_type, body.scope_id)
    if not user or scope_organization is None or (principal.organization_id and (user.organization_id != principal.organization_id or scope_organization != principal.organization_id)) or (user.organization_id and user.organization_id != scope_organization):
        raise HTTPException(404, "User or location was not found.")
    item = session.scalar(select(LocationAccessRecord).where(LocationAccessRecord.user_id == user.id, LocationAccessRecord.scope_type == body.scope_type, LocationAccessRecord.scope_id == body.scope_id))
    if item:
        item.permission = body.permission
    else:
        item = LocationAccessRecord(user_id=user.id, scope_type=body.scope_type, scope_id=body.scope_id, permission=body.permission, created_at=datetime.now(UTC)); session.add(item)
    session.commit(); session.refresh(item)
    return {"id": str(item.id), "user_id": str(item.user_id), "scope_type": item.scope_type, "scope_id": str(item.scope_id), "permission": item.permission}


@router.delete("/access/{access_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_access(access_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    item = session.get(LocationAccessRecord, access_id); user = session.get(UserRecord, item.user_id) if item else None
    if not item or not user or (principal.organization_id and user.organization_id != principal.organization_id):
        raise HTTPException(404, "Location access was not found.")
    session.delete(item); session.commit()
