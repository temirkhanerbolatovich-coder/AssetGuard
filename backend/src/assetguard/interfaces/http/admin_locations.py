from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.admin_assets import _pdf_font_name, require_admin, require_viewer
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.incidents.models import (
    AssetHistoryEntryRecord, EndpointHistoryEntryRecord, IncidentRecord,
    PhysicalIncidentDecisionRecord, PhysicalIncidentRecord,
)
from assetguard.modules.assets.models import (
    AssetRecord, BuildingRecord, FloorRecord, OrganizationRecord, RoomInspectionItemRecord,
    RoomInspectionRecord, RoomRecord,
)
from assetguard.modules.history.service import append_asset_history
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.identity.location_access import permitted_room_ids, require_room_access
from assetguard.modules.identity.models import LocationAccessRecord, UserRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord
from assetguard.modules.vision.models import VisionBaselineRecord, VisionRoomRecord, VisionScanRecord

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


class RoomInspectionItemInput(BaseModel):
    asset_id: UUID
    result: Literal["PRESENT", "MISSING", "DAMAGED"]
    affected_quantity: int = Field(default=0, ge=0, le=1_000_000)
    comment: str | None = Field(default=None, max_length=2000)


class RoomInspectionCreate(BaseModel):
    comment: str | None = Field(default=None, max_length=4000)
    items: list[RoomInspectionItemInput]


class PhysicalIncidentDecisionInput(BaseModel):
    action: Literal["INVESTIGATE", "MOVE", "REPAIR", "WRITE_OFF", "FALSE_POSITIVE"]
    comment: str = Field(min_length=3, max_length=4000)
    quantity: int | None = Field(default=None, ge=1, le=1_000_000)
    destination_room_id: UUID | None = None
    destination_inventory_number: str | None = Field(default=None, min_length=1, max_length=128)
    document_number: str | None = Field(default=None, min_length=1, max_length=128)


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


def _inspection_view(session: Session, inspection: RoomInspectionRecord) -> dict:
    items = list(session.scalars(select(RoomInspectionItemRecord).where(
        RoomInspectionItemRecord.inspection_id == inspection.id,
    )))
    assets = {asset.id: asset for asset in session.scalars(select(AssetRecord).where(
        AssetRecord.id.in_([item.asset_id for item in items]),
    ))} if items else {}
    items.sort(key=lambda item: (
        assets[item.asset_id].inventory_number if item.asset_id in assets else "",
        str(item.asset_id),
    ))
    counts = {"PRESENT": 0, "MISSING": 0, "DAMAGED": 0}
    for item in items:
        counts[item.result] += 1
    return {
        "id": str(inspection.id), "room_id": str(inspection.room_id),
        "inspector_name": inspection.inspector_name, "comment": inspection.comment,
        "completed_at": inspection.completed_at, "counts": counts,
        "items": [{
            "id": str(item.id), "asset_id": str(item.asset_id),
            "inventory_number": assets[item.asset_id].inventory_number if item.asset_id in assets else None,
            "name": assets[item.asset_id].name if item.asset_id in assets else "Удалённая позиция",
            "result": item.result, "expected_quantity": item.expected_quantity,
            "affected_quantity": item.affected_quantity, "comment": item.comment,
        } for item in items],
    }


def _room_path(session: Session, room_id: UUID | None) -> str:
    room = session.get(RoomRecord, room_id) if room_id else None
    floor = session.get(FloorRecord, room.floor_id) if room else None
    building = session.get(BuildingRecord, floor.building_id) if floor else None
    return " / ".join(value for value in (
        building.name if building else None, floor.name if floor else None, room.name if room else None,
    ) if value) or "Без кабинета"


def _place_asset(session: Session, asset: AssetRecord, room: RoomRecord | None) -> None:
    if room is None:
        asset.room_id = None
        asset.building = asset.floor = asset.room = None
        return
    floor = session.get(FloorRecord, room.floor_id)
    building = session.get(BuildingRecord, floor.building_id) if floor else None
    if not floor or not building or building.organization_id != asset.organization_id:
        raise HTTPException(422, "The selected room does not belong to the asset organization.")
    asset.room_id, asset.building, asset.floor, asset.room = room.id, building.name, floor.name, room.name


def _physical_incident_view(session: Session, incident: PhysicalIncidentRecord) -> dict:
    asset = session.get(AssetRecord, incident.asset_id)
    decisions = list(session.scalars(select(PhysicalIncidentDecisionRecord).where(
        PhysicalIncidentDecisionRecord.incident_id == incident.id,
    ).order_by(PhysicalIncidentDecisionRecord.created_at)))
    return {
        "id": str(incident.id), "room_id": str(incident.room_id),
        "asset_id": str(incident.asset_id),
        "inventory_number": asset.inventory_number if asset else None,
        "asset_name": asset.name if asset else "Удалённая позиция",
        "issue_type": incident.issue_type, "affected_quantity": incident.affected_quantity,
        "status": incident.status, "severity": incident.severity,
        "title": incident.title, "description": incident.description,
        "created_at": incident.created_at, "resolved_at": incident.resolved_at,
        "decisions": [{
            "id": str(decision.id), "action": decision.action,
            "comment": decision.comment, "actor": decision.actor,
            "quantity": decision.quantity, "document_number": decision.document_number,
            "source_room_id": str(decision.source_room_id) if decision.source_room_id else None,
            "destination_room_id": str(decision.destination_room_id) if decision.destination_room_id else None,
            "destination_asset_id": str(decision.destination_asset_id) if decision.destination_asset_id else None,
            "operation_snapshot": decision.operation_snapshot,
            "has_act": decision.action in {"MOVE", "WRITE_OFF"} and bool(decision.document_number),
            "created_at": decision.created_at,
        } for decision in decisions],
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
            # An administrator must see an empty floor in order to add its first
            # room. Scoped users still see only floors containing rooms they may access.
            if rooms or allowed_rooms is None:
                floors.append({"id": str(floor.id), "name": floor.name, "responsible_name": floor.responsible_name, "responsible_contact": floor.responsible_contact, "rooms": [_room_view(session, room) for room in rooms]})
        # A building is meaningful as soon as it is created.  In particular,
        # administrators need to see an empty building in order to add its
        # first floor.  Previously it was omitted until it contained a room,
        # which made a successfully created building look like it had vanished.
        result.append({"id": str(building.id), "organization_id": str(building.organization_id), "name": building.name, "responsible_name": building.responsible_name, "responsible_contact": building.responsible_contact, "notes": building.notes, "floors": floors})
    return result


@router.get("/organizations")
def organizations(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    query = select(OrganizationRecord).order_by(OrganizationRecord.created_at, OrganizationRecord.name)
    if principal.organization_id:
        query = query.where(OrganizationRecord.id == principal.organization_id)
    return [{"id": str(item.id), "name": item.name} for item in session.scalars(query)]


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


@router.get("/rooms/{room_id}/inspections")
def room_inspections(room_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    room = _room(session, room_id, principal)
    inspections = session.scalars(select(RoomInspectionRecord).where(
        RoomInspectionRecord.room_id == room.id,
    ).order_by(RoomInspectionRecord.completed_at.desc()).limit(50))
    return [_inspection_view(session, item) for item in inspections]


@router.post("/rooms/{room_id}/inspections", status_code=status.HTTP_201_CREATED)
def create_room_inspection(room_id: UUID, body: RoomInspectionCreate, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    room = _room(session, room_id, principal)
    require_room_access(session, room.id, principal, write=True)
    assets = list(session.scalars(select(AssetRecord).where(
        AssetRecord.room_id == room.id,
    ).order_by(AssetRecord.inventory_number)))
    if not assets:
        raise HTTPException(409, "The room has no assets to inspect.")
    expected_ids = {asset.id for asset in assets}
    submitted_ids = [item.asset_id for item in body.items]
    if len(submitted_ids) != len(set(submitted_ids)) or set(submitted_ids) != expected_ids:
        raise HTTPException(422, "Every asset in the room must have exactly one inspection result.")
    assets_by_id = {asset.id: asset for asset in assets}
    for item in body.items:
        expected_quantity = assets_by_id[item.asset_id].quantity
        if item.result == "PRESENT" and item.affected_quantity != 0:
            raise HTTPException(422, "Present assets cannot have an affected quantity.")
        if item.result != "PRESENT" and not 1 <= item.affected_quantity <= expected_quantity:
            raise HTTPException(422, "Missing or damaged assets require an affected quantity within the expected total.")
    now = datetime.now(UTC)
    inspection = RoomInspectionRecord(
        room_id=room.id, inspector_user_id=principal.user_id,
        inspector_name=principal.username, comment=_clean(body.comment), completed_at=now,
    )
    session.add(inspection); session.flush()
    labels = {"PRESENT": "на месте", "MISSING": "отсутствует", "DAMAGED": "повреждено"}
    inspection_items: list[tuple[RoomInspectionItemInput, RoomInspectionItemRecord]] = []
    for item in body.items:
        asset = assets_by_id[item.asset_id]
        record = RoomInspectionItemRecord(
            inspection_id=inspection.id, asset_id=asset.id, result=item.result,
            expected_quantity=asset.quantity, affected_quantity=item.affected_quantity,
            comment=_clean(item.comment),
        )
        session.add(record)
        inspection_items.append((item, record))
        message = f"Физическая проверка: {labels[item.result]}."
        if item.affected_quantity:
            message = f"Физическая проверка: {labels[item.result]} — {item.affected_quantity} из {asset.quantity} {asset.unit}."
        append_asset_history(
            session, asset_id=asset.id, event_type="PHYSICAL_INSPECTION_COMPLETED",
            related_entity_type="ROOM_INSPECTION", related_entity_id=inspection.id,
            message=message, metadata={"result": item.result, "affected_quantity": item.affected_quantity, "inspector": principal.username},
        )
    session.flush()
    for item, record in inspection_items:
        if item.result == "PRESENT":
            continue
        asset = assets_by_id[item.asset_id]
        incident = PhysicalIncidentRecord(
            room_id=room.id, asset_id=asset.id, inspection_item_id=record.id,
            issue_type=item.result, affected_quantity=item.affected_quantity,
            status="OPEN", severity="HIGH" if item.result == "MISSING" else "MEDIUM",
            title=f"{asset.name}: {labels[item.result]}",
            description=_clean(item.comment) or f"Расхождение обнаружено при физическом обходе кабинета {room.name}.",
            created_at=now, resolved_at=None,
        )
        session.add(incident); session.flush()
        append_asset_history(
            session, asset_id=asset.id, event_type="PHYSICAL_INCIDENT_CREATED",
            related_entity_type="PHYSICAL_INCIDENT", related_entity_id=incident.id,
            message=f"Создан физический инцидент: {labels[item.result]} — {item.affected_quantity} из {asset.quantity} {asset.unit}.",
            metadata={"inspection_id": str(inspection.id), "inspection_item_id": str(record.id), "severity": incident.severity},
        )
    session.commit(); session.refresh(inspection)
    return _inspection_view(session, inspection)


@router.post("/physical-incidents/{incident_id}/decision")
def decide_physical_incident(
    incident_id: UUID, body: PhysicalIncidentDecisionInput,
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_viewer)],
):
    incident = session.get(PhysicalIncidentRecord, incident_id, with_for_update=True)
    if not incident:
        raise HTTPException(404, "Physical incident was not found.")
    _room(session, incident.room_id, principal)
    require_room_access(session, incident.room_id, principal, write=True)
    if incident.status == "RESOLVED":
        raise HTTPException(409, "The physical incident is already resolved.")
    now = datetime.now(UTC)
    asset = session.get(AssetRecord, incident.asset_id, with_for_update=True)
    if not asset:
        raise HTTPException(409, "The asset linked to this incident no longer exists.")
    if asset.room_id != incident.room_id:
        raise HTTPException(409, "The asset location changed after the inspection. Start a new inspection before processing it.")
    organization = session.get(OrganizationRecord, asset.organization_id)
    source_room_id = asset.room_id
    destination_room = None
    destination_asset = None
    operation_snapshot = None
    quantity = body.quantity
    document_number = _clean(body.document_number)

    if body.action in {"MOVE", "WRITE_OFF"}:
        if quantity is None or quantity > incident.affected_quantity or quantity > asset.quantity:
            raise HTTPException(422, "Quantity must be within both the incident amount and the current asset balance.")
        if not document_number:
            raise HTTPException(422, "Document number is required for move and write-off operations.")
        if asset.tracking_mode == "INDIVIDUAL" and quantity != asset.quantity:
            raise HTTPException(422, "An individually tracked asset can only be processed in full.")

    if body.action == "MOVE":
        if body.destination_room_id is None:
            raise HTTPException(422, "Destination room is required for a move.")
        destination_room = _room(session, body.destination_room_id, principal)
        require_room_access(session, destination_room.id, principal, write=True)
        if destination_room.id == source_room_id:
            raise HTTPException(422, "Choose a different destination room.")
        before_quantity = asset.quantity
        source_path, destination_path = _room_path(session, source_room_id), _room_path(session, destination_room.id)
        if quantity < asset.quantity:
            if asset.tracking_mode != "GROUPED":
                raise HTTPException(422, "Only a grouped asset position can be split.")
            inventory_number = _clean(body.destination_inventory_number)
            if not inventory_number:
                raise HTTPException(422, "A new inventory number is required for a partial move.")
            duplicate = session.scalar(select(AssetRecord).where(
                AssetRecord.organization_id == asset.organization_id,
                AssetRecord.inventory_number == inventory_number,
            ))
            if duplicate:
                raise HTTPException(409, "The destination inventory number already exists.")
            asset.quantity -= quantity
            destination_asset = AssetRecord(
                organization_id=asset.organization_id, inventory_number=inventory_number,
                name=asset.name, asset_type=asset.asset_type, category=asset.category,
                tracking_mode=asset.tracking_mode, quantity=quantity, unit=asset.unit,
                status=asset.status, building=None, floor=None, room=None,
                notes=asset.notes, created_at=now, updated_at=now,
            )
            _place_asset(session, destination_asset, destination_room)
            session.add(destination_asset); session.flush()
            append_asset_history(
                session, asset_id=destination_asset.id, event_type="ASSET_CREATED",
                related_entity_type="PHYSICAL_INCIDENT", related_entity_id=incident.id,
                message=f"Позиция создана при частичном перемещении из {source_path} по акту {document_number}.",
                metadata={"source_asset_id": str(asset.id), "quantity": quantity, "document_number": document_number},
            )
        else:
            destination_asset = asset
            _place_asset(session, asset, destination_room)
        asset.updated_at = now
        operation_snapshot = {
            "asset_name": asset.name, "inventory_number": asset.inventory_number,
            "organization_name": organization.name if organization else "AssetGuard",
            "source_path": source_path, "destination_path": destination_path,
            "quantity": quantity, "unit": asset.unit, "balance_before": before_quantity,
            "balance_after": asset.quantity if destination_asset is not asset else asset.quantity,
            "destination_inventory_number": destination_asset.inventory_number,
        }
        append_asset_history(
            session, asset_id=asset.id, event_type="ASSET_MOVED",
            related_entity_type="PHYSICAL_INCIDENT", related_entity_id=incident.id,
            message=f"Перемещено {quantity} {asset.unit}: {source_path} → {destination_path}. Акт {document_number}.",
            metadata=operation_snapshot | {"actor": principal.username, "document_number": document_number},
        )
    elif body.action == "WRITE_OFF":
        before_quantity = asset.quantity
        source_path = _room_path(session, source_room_id)
        if quantity < asset.quantity:
            if asset.tracking_mode != "GROUPED":
                raise HTTPException(422, "Only a grouped asset position can be written off partially.")
            asset.quantity -= quantity
        else:
            asset.status = "WRITTEN_OFF"
            _place_asset(session, asset, None)
        asset.updated_at = now
        operation_snapshot = {
            "asset_name": asset.name, "inventory_number": asset.inventory_number,
            "organization_name": organization.name if organization else "AssetGuard",
            "source_path": source_path, "quantity": quantity, "unit": asset.unit,
            "balance_before": before_quantity, "balance_after": 0 if quantity == before_quantity else asset.quantity,
        }
        append_asset_history(
            session, asset_id=asset.id, event_type="ASSET_WRITTEN_OFF",
            related_entity_type="PHYSICAL_INCIDENT", related_entity_id=incident.id,
            message=f"Списано {quantity} {asset.unit} из {source_path}. Акт {document_number}.",
            metadata=operation_snapshot | {"actor": principal.username, "document_number": document_number},
        )

    decision = PhysicalIncidentDecisionRecord(
        incident_id=incident.id, action=body.action, comment=_clean(body.comment),
        actor=principal.username, source_room_id=source_room_id,
        destination_room_id=destination_room.id if destination_room else None,
        destination_asset_id=destination_asset.id if destination_asset else None,
        quantity=quantity if body.action in {"MOVE", "WRITE_OFF"} else None,
        document_number=document_number if body.action in {"MOVE", "WRITE_OFF"} else None,
        operation_snapshot=operation_snapshot, created_at=now,
    )
    session.add(decision)
    resolving = body.action != "INVESTIGATE"
    incident.status = "RESOLVED" if resolving else "UNDER_REVIEW"
    incident.resolved_at = now if resolving else None
    action_labels = {
        "INVESTIGATE": "назначена дополнительная проверка", "MOVE": "принято решение о перемещении",
        "REPAIR": "передано в ремонт", "WRITE_OFF": "принято решение о списании",
        "FALSE_POSITIVE": "расхождение не подтвердилось",
    }
    append_asset_history(
        session, asset_id=incident.asset_id,
        event_type="PHYSICAL_INCIDENT_RESOLVED" if resolving else "PHYSICAL_INCIDENT_CLASSIFIED",
        related_entity_type="PHYSICAL_INCIDENT", related_entity_id=incident.id,
        message=f"Физический инцидент: {action_labels[body.action]}.",
        metadata={"action": body.action, "actor": principal.username, "comment": body.comment,
                  "quantity": quantity, "document_number": document_number},
    )
    session.commit(); session.refresh(incident)
    return _physical_incident_view(session, incident)


def _physical_operation_pdf(incident: PhysicalIncidentRecord, decision: PhysicalIncidentDecisionRecord) -> BytesIO:
    snapshot = decision.operation_snapshot or {}
    font = _pdf_font_name()
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("OperationTitle", parent=styles["Title"], fontName=font, fontSize=17, leading=22, alignment=TA_CENTER)
    text_style = ParagraphStyle("OperationText", parent=styles["Normal"], fontName=font, fontSize=10, leading=15)
    heading_style = ParagraphStyle("OperationHeading", parent=text_style, fontSize=12, leading=17)
    action_name = "перемещения" if decision.action == "MOVE" else "списания"
    values = [
        ("Организация", str(snapshot.get("organization_name") or "AssetGuard")),
        ("Номер акта", decision.document_number or "—"),
        ("Дата и время", decision.created_at.astimezone().strftime("%d.%m.%Y %H:%M")),
        ("Операция", "Перемещение имущества" if decision.action == "MOVE" else "Списание имущества"),
        ("Наименование", str(snapshot.get("asset_name") or "—")),
        ("Инвентарный номер", str(snapshot.get("inventory_number") or "—")),
        ("Количество", f"{decision.quantity or '—'} {snapshot.get('unit') or ''}".strip()),
        ("Исходное место", str(snapshot.get("source_path") or "—")),
    ]
    if decision.action == "MOVE":
        values.extend([
            ("Новое место", str(snapshot.get("destination_path") or "—")),
            ("Инв. номер после перемещения", str(snapshot.get("destination_inventory_number") or snapshot.get("inventory_number") or "—")),
        ])
    values.extend([("Основание / комментарий", decision.comment or "—"), ("Операцию выполнил", decision.actor)])
    rows = [[Paragraph(escape(label), text_style), Paragraph(escape(value), text_style)] for label, value in values]
    table = Table(rows, colWidths=[58 * mm, 115 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story = [
        Paragraph(f"АКТ {action_name.upper()} ИМУЩЕСТВА", title), Spacer(1, 4 * mm),
        Paragraph(f"Сформирован системой AssetGuard по физическому инциденту {incident.id}.", heading_style),
        Spacer(1, 6 * mm), table, Spacer(1, 18 * mm),
        Paragraph("Ответственный: ____________________ / ____________________", text_style),
        Spacer(1, 9 * mm), Paragraph("Подтверждение принимающей стороны: ____________________", text_style),
    ]
    document.build(story)
    output.seek(0)
    return output


@router.get("/physical-incidents/{incident_id}/act.pdf")
def physical_incident_act(
    incident_id: UUID, session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_viewer)],
):
    incident = session.get(PhysicalIncidentRecord, incident_id)
    if not incident:
        raise HTTPException(404, "Physical incident was not found.")
    _room(session, incident.room_id, principal)
    decision = session.scalar(select(PhysicalIncidentDecisionRecord).where(
        PhysicalIncidentDecisionRecord.incident_id == incident.id,
        PhysicalIncidentDecisionRecord.action.in_(("MOVE", "WRITE_OFF")),
    ).order_by(PhysicalIncidentDecisionRecord.created_at.desc()))
    if not decision or not decision.document_number:
        raise HTTPException(409, "A move or write-off act has not been created for this incident.")
    safe_number = "".join(character if character.isalnum() or character in "-_" else "-" for character in decision.document_number)
    return StreamingResponse(
        _physical_operation_pdf(incident, decision), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="assetguard-act-{safe_number}.pdf"'},
    )


@router.get("/rooms/{room_id}/workspace")
def room_workspace(room_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    """Return one room's inventory, evidence state and outstanding decisions.

    This is deliberately a room-level read model: it lets the interface keep
    baseline, observations and incidents together without exposing another
    room's data to a location-scoped user.
    """
    room = _room(session, room_id, principal)
    floor = session.get(FloorRecord, room.floor_id)
    building = session.get(BuildingRecord, floor.building_id) if floor else None
    assets = list(session.scalars(select(AssetRecord).where(AssetRecord.room_id == room.id).order_by(AssetRecord.category, AssetRecord.name, AssetRecord.inventory_number)))
    asset_ids = [asset.id for asset in assets]
    endpoints = list(session.scalars(select(ManagedEndpointRecord).where(ManagedEndpointRecord.asset_id.in_(asset_ids)))) if asset_ids else []
    endpoint_ids = [endpoint.id for endpoint in endpoints]
    active_baseline_ids = set(session.scalars(select(BaselineRecord.managed_endpoint_id).where(BaselineRecord.managed_endpoint_id.in_(endpoint_ids), BaselineRecord.status == "ACTIVE"))) if endpoint_ids else set()
    incidents = list(session.scalars(select(IncidentRecord).where(IncidentRecord.managed_endpoint_id.in_(endpoint_ids), IncidentRecord.status.in_(("OPEN", "UNDER_REVIEW"))).order_by(IncidentRecord.created_at.desc()))) if endpoint_ids else []
    physical_incidents = list(session.scalars(select(PhysicalIncidentRecord).where(
        PhysicalIncidentRecord.room_id == room.id,
    ).order_by(PhysicalIncidentRecord.created_at.desc()).limit(50)))
    vision_room = session.scalar(select(VisionRoomRecord).where(VisionRoomRecord.location_room_id == room.id))
    vision_baseline = session.scalar(select(VisionBaselineRecord).where(VisionBaselineRecord.room_id == vision_room.id)) if vision_room else None
    vision_scans = list(session.scalars(select(VisionScanRecord).where(VisionScanRecord.room_id == vision_room.id).order_by(VisionScanRecord.created_at.desc()).limit(50))) if vision_room else []
    inspections = list(session.scalars(select(RoomInspectionRecord).where(RoomInspectionRecord.room_id == room.id).order_by(RoomInspectionRecord.completed_at.desc()).limit(20)))
    inspection_views = [_inspection_view(session, item) for item in inspections]
    latest_scan = vision_scans[0] if vision_scans else None
    history = []
    if asset_ids:
        history.extend({"id": str(item.id), "type": item.event_type, "occurred_at": item.occurred_at, "message": item.message, "source": "ASSET", "entity_id": str(item.asset_id)} for item in session.scalars(select(AssetHistoryEntryRecord).where(AssetHistoryEntryRecord.asset_id.in_(asset_ids)).order_by(AssetHistoryEntryRecord.occurred_at.desc()).limit(50)))
    if endpoint_ids:
        history.extend({"id": str(item.id), "type": item.event_type, "occurred_at": item.occurred_at, "message": item.message, "source": "AGENT", "entity_id": str(item.managed_endpoint_id)} for item in session.scalars(select(EndpointHistoryEntryRecord).where(EndpointHistoryEntryRecord.managed_endpoint_id.in_(endpoint_ids)).order_by(EndpointHistoryEntryRecord.occurred_at.desc()).limit(50)))
    history.extend({"id": str(item.id), "type": "VISION_SCAN_COMPLETED", "occurred_at": item.created_at, "message": f"Фотопроверка завершена со статусом {item.status}.", "source": "VISION", "entity_id": str(item.id)} for item in vision_scans)
    history.extend({"id": str(item.id), "type": "PHYSICAL_INSPECTION_COMPLETED", "occurred_at": item.completed_at, "message": f"Физический обход завершил {item.inspector_name}.", "source": "PHYSICAL", "entity_id": str(item.id)} for item in inspections)
    history.sort(key=lambda item: item["occurred_at"], reverse=True)
    categories: dict[str, dict[str, int | str]] = {}
    for asset in assets:
        bucket = categories.setdefault(asset.category, {"category": asset.category, "positions": 0, "quantity": 0})
        bucket["positions"] = int(bucket["positions"]) + 1
        bucket["quantity"] = int(bucket["quantity"]) + asset.quantity
    return {
        "room": _room_view(session, room),
        "path": {"building": building.name if building else None, "floor": floor.name if floor else None},
        "inventory": {
            "positions": len(assets), "quantity": sum(asset.quantity for asset in assets),
            "categories": list(categories.values()),
            "assets": [{"id": str(asset.id), "inventory_number": asset.inventory_number, "name": asset.name, "asset_type": asset.asset_type, "category": asset.category, "tracking_mode": asset.tracking_mode, "quantity": asset.quantity, "unit": asset.unit, "status": asset.status} for asset in assets],
        },
        "agents": [{"id": str(endpoint.id), "asset_id": str(endpoint.asset_id) if endpoint.asset_id else None, "hostname": endpoint.hostname, "status": endpoint.status, "last_seen_at": endpoint.last_seen_at, "has_baseline": endpoint.id in active_baseline_ids} for endpoint in endpoints],
        "baseline": {"agent_ready": len(active_baseline_ids), "agent_total": len(endpoints), "vision_ready": vision_baseline is not None},
        "vision": None if not vision_room else {"room_id": str(vision_room.id), "has_baseline": vision_baseline is not None, "baseline_counts": vision_baseline.counts if vision_baseline else None, "latest_scan": None if not latest_scan else {"id": str(latest_scan.id), "status": latest_scan.status, "created_at": latest_scan.created_at, "counts": latest_scan.counts, "comparison": latest_scan.comparison}},
        "incidents": [{"id": str(item.id), "endpoint_id": str(item.managed_endpoint_id), "status": item.status, "severity": item.severity, "title": item.title, "created_at": item.created_at} for item in incidents],
        "physical_incidents": [_physical_incident_view(session, item) for item in physical_incidents],
        "inspections": inspection_views,
        "latest_inspection": inspection_views[0] if inspection_views else None,
        "history": history[:50],
    }


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
