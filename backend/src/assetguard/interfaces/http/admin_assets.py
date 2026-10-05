from __future__ import annotations

import re
from decimal import Decimal
from html import escape
from io import BytesIO
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from openpyxl import Workbook, load_workbook
import pdfplumber
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.authorization import require_admin, require_viewer
from assetguard.interfaces.http.pdf_support import pdf_font_name
from assetguard.interfaces.http.qr_support import qr_base_url, qr_svg_response
from assetguard.interfaces.http.resource_scope import scoped_endpoint
from assetguard.modules.assets.models import AssetRecord, OrganizationRecord, RoomRecord, FloorRecord, BuildingRecord
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.history.service import append_asset_history
from assetguard.modules.endpoints.service import evaluate_last_seen
from assetguard.modules.incidents.models import (
    AssetHistoryEntryRecord, IncidentRecord, PhysicalIncidentDecisionRecord, PhysicalIncidentRecord,
)
from assetguard.modules.inventory.models import RawInventoryRecord
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.identity.location_access import permitted_room_ids, require_room_access
from assetguard.modules.snapshots.models import (
    ComponentObservationRecord, EndpointIdentifierRecord,
    HardwareSnapshotRecord, ManagedEndpointRecord,
)

router = APIRouter(prefix="/admin", tags=["admin"])


AssetType = Literal["Desktop", "Laptop", "Printer", "Projector", "Network", "Furniture", "Sports", "Educational", "Other"]
AssetCategory = Literal["IT", "FURNITURE", "SPORTS", "EDUCATIONAL", "OTHER"]
TrackingMode = Literal["INDIVIDUAL", "GROUPED"]
ImportRow = dict[str, str | int | bool | None]
SUPPORTED_AGENT_VERSIONS = frozenset({"1.19", "1.20"})
ASSETGUARD_INSTALLER_TAG_PREFIX = "assetguard-installer-"


class AssetCreate(BaseModel):
    inventory_number: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    asset_type: AssetType
    category: AssetCategory = "IT"
    tracking_mode: TrackingMode = "INDIVIDUAL"
    quantity: int = Field(default=1, ge=1, le=1_000_000)
    unit: str = Field(default="шт.", min_length=1, max_length=32)
    status: str = Field(default="ACTIVE", max_length=32)
    building: str | None = Field(default=None, max_length=255)
    floor: str | None = Field(default=None, max_length=64)
    room: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    room_id: UUID | None = None


class AssetUpdate(BaseModel):
    inventory_number: str | None = Field(default=None, min_length=1, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_type: AssetType | None = None
    category: AssetCategory | None = None
    tracking_mode: TrackingMode | None = None
    quantity: int | None = Field(default=None, ge=1, le=1_000_000)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    status: str | None = Field(default=None, max_length=32)
    building: str | None = Field(default=None, max_length=255)
    floor: str | None = Field(default=None, max_length=64)
    room: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    room_id: UUID | None = None


def _asset_view(asset: AssetRecord, endpoint_id: UUID | None, organization: str | None = None) -> dict:
    return {
        "id": str(asset.id), "inventory_number": asset.inventory_number,
        "name": asset.name, "asset_type": asset.asset_type, "status": asset.status,
        "category": asset.category, "tracking_mode": asset.tracking_mode, "quantity": asset.quantity, "unit": asset.unit,
        "building": asset.building, "floor": asset.floor, "room": asset.room,
        "room_id": str(asset.room_id) if asset.room_id else None,
        "notes": asset.notes, "organization": organization,
        "endpoint_id": str(endpoint_id) if endpoint_id else None,
    }


def _organization_for_name(session: Session, name: str) -> OrganizationRecord:
    organization = session.scalar(select(OrganizationRecord).where(OrganizationRecord.name == name))
    if organization:
        return organization
    organization = OrganizationRecord(name=name, created_at=datetime.now(UTC))
    session.add(organization)
    session.flush()
    return organization


def _scoped_asset(session: Session, asset_id: UUID, principal: AuthPrincipal) -> AssetRecord:
    asset = session.get(AssetRecord, asset_id)
    if not asset or (principal.organization_id and asset.organization_id != principal.organization_id):
        raise HTTPException(404, "Asset was not found.")
    require_room_access(session, asset.room_id, principal)
    return asset


def _apply_room_location(asset: AssetRecord, room_id: UUID | None, session: Session, organization_id: UUID) -> None:
    if room_id is None:
        asset.room_id = None
        return
    room = session.get(RoomRecord, room_id)
    floor = session.get(FloorRecord, room.floor_id) if room else None
    building = session.get(BuildingRecord, floor.building_id) if floor else None
    if not room or not floor or not building or building.organization_id != organization_id:
        raise HTTPException(422, "The selected room does not belong to this organization.")
    asset.room_id = room.id
    # Keep the legacy fields in sync for existing exports and integrations.
    asset.building, asset.floor, asset.room = building.name, floor.name, room.name


def _ensure_room_for_legacy_location(asset: AssetRecord, session: Session) -> None:
    """Turn legacy text fields into managed locations while preserving import compatibility."""
    if not asset.room:
        return
    building_name, floor_name = asset.building or "Не указан корпус", asset.floor or "Не указан этаж"
    building = session.scalar(select(BuildingRecord).where(BuildingRecord.organization_id == asset.organization_id, BuildingRecord.name == building_name))
    if not building:
        building = BuildingRecord(organization_id=asset.organization_id, name=building_name, created_at=datetime.now(UTC)); session.add(building); session.flush()
    floor = session.scalar(select(FloorRecord).where(FloorRecord.building_id == building.id, FloorRecord.name == floor_name))
    if not floor:
        floor = FloorRecord(building_id=building.id, name=floor_name, created_at=datetime.now(UTC)); session.add(floor); session.flush()
    room = session.scalar(select(RoomRecord).where(RoomRecord.floor_id == floor.id, RoomRecord.name == asset.room))
    if not room:
        room = RoomRecord(floor_id=floor.id, name=asset.room, created_at=datetime.now(UTC)); session.add(room); session.flush()
    asset.room_id = room.id


def _latest_observed_snapshot(session: Session, endpoint_id: UUID) -> HardwareSnapshotRecord | None:
    snapshots = session.scalars(select(HardwareSnapshotRecord).where(
        HardwareSnapshotRecord.managed_endpoint_id == endpoint_id,
    ).order_by(HardwareSnapshotRecord.captured_at.desc()).limit(50))
    return next((snapshot for snapshot in snapshots if session.scalar(
        select(func.count()).select_from(ComponentObservationRecord).where(
            ComponentObservationRecord.hardware_snapshot_id == snapshot.id,
        )
    )), None)


def _latest_components(session: Session, endpoint_id: UUID) -> list[ComponentObservationRecord]:
    result: list[ComponentObservationRecord] = []
    observed_types: set[str] = set()
    snapshots = session.scalars(select(HardwareSnapshotRecord).where(
        HardwareSnapshotRecord.managed_endpoint_id == endpoint_id,
    ).order_by(HardwareSnapshotRecord.captured_at.desc()).limit(50))
    for snapshot in snapshots:
        observations = list(session.scalars(select(ComponentObservationRecord).where(
            ComponentObservationRecord.hardware_snapshot_id == snapshot.id,
        )))
        for component_type in {item.component_type for item in observations} - observed_types:
            result.extend(item for item in observations if item.component_type == component_type)
            observed_types.add(component_type)
    return result


def _ram_capacity_bytes(value: int | None) -> int | None:
    """Accept both GLPI's legacy MiB values and byte-based inventory payloads."""
    if value is None:
        return None
    return value * 1024 * 1024 if value < 1024 * 1024 else value


def _component_view(item: ComponentObservationRecord) -> dict:
    return {
        "type": item.component_type, "model": item.model, "serial": item.serial_number,
        "manufacturer": item.manufacturer, "part_number": item.part_number,
        "capacity": _ram_capacity_bytes(item.capacity) if item.component_type == "RAM" else item.capacity,
        "slot": item.slot, "confidence": item.confidence,
        "raw_data": item.raw_data,
    }


def _endpoint_summaries(session: Session, endpoints: list[ManagedEndpointRecord]) -> dict[UUID, dict]:
    """Read only scoped endpoints; retain each component type's latest observed state.

    Limit history to 50 snapshots per endpoint before joining observations, so an
    empty or partial inventory keeps known hardware without loading all history.
    """
    if not endpoints:
        return {}
    endpoint_ids = [endpoint.id for endpoint in endpoints]
    ranked_snapshots = select(
        HardwareSnapshotRecord.id,
        func.row_number().over(
            partition_by=HardwareSnapshotRecord.managed_endpoint_id,
            order_by=HardwareSnapshotRecord.captured_at.desc(),
        ).label("position"),
    ).where(HardwareSnapshotRecord.managed_endpoint_id.in_(endpoint_ids)).subquery()
    snapshot_rows = session.execute(
        select(HardwareSnapshotRecord, ComponentObservationRecord)
        .join(ranked_snapshots, ranked_snapshots.c.id == HardwareSnapshotRecord.id)
        .outerjoin(ComponentObservationRecord, ComponentObservationRecord.hardware_snapshot_id == HardwareSnapshotRecord.id)
        .where(ranked_snapshots.c.position <= 50)
        .order_by(HardwareSnapshotRecord.managed_endpoint_id, ranked_snapshots.c.position)
    )
    latest_snapshots: dict[UUID, HardwareSnapshotRecord] = {}
    components: dict[UUID, list[ComponentObservationRecord]] = {}
    observed_snapshots: dict[UUID, dict[str, UUID]] = {}
    for snapshot, observation in snapshot_rows:
        endpoint_id = snapshot.managed_endpoint_id
        latest_snapshots.setdefault(endpoint_id, snapshot)
        if observation is None:
            continue
        observed_types = observed_snapshots.setdefault(endpoint_id, {})
        selected_snapshot = observed_types.setdefault(observation.component_type, snapshot.id)
        if selected_snapshot == snapshot.id:
            components.setdefault(endpoint_id, []).append(observation)
    open_changes = dict(session.execute(select(
        ChangeEventRecord.managed_endpoint_id, func.count(),
    ).where(
        ChangeEventRecord.managed_endpoint_id.in_(endpoint_ids), ChangeEventRecord.status == "OPEN",
    ).group_by(ChangeEventRecord.managed_endpoint_id)).all())
    open_incidents = dict(session.execute(select(
        IncidentRecord.managed_endpoint_id, func.count(),
    ).where(
        IncidentRecord.managed_endpoint_id.in_(endpoint_ids), IncidentRecord.status.in_(("OPEN", "UNDER_REVIEW")),
    ).group_by(IncidentRecord.managed_endpoint_id)).all())
    return {
        endpoint.id: _endpoint_summary_view(
            endpoint, latest_snapshots.get(endpoint.id), components.get(endpoint.id, []),
            open_changes.get(endpoint.id, 0), open_incidents.get(endpoint.id, 0),
        )
        for endpoint in endpoints
    }


def _endpoint_summary(session: Session, endpoint: ManagedEndpointRecord) -> dict:
    return _endpoint_summaries(session, [endpoint])[endpoint.id]


def _endpoint_summary_view(
    endpoint: ManagedEndpointRecord, snapshot: HardwareSnapshotRecord | None,
    observations: list[ComponentObservationRecord], open_changes: int, open_incidents: int,
) -> dict:
    ram = [item for item in observations if item.component_type == "RAM"]
    storage = [item for item in observations if item.component_type == "STORAGE"]
    cpu = next((item for item in observations if item.component_type == "CPU"), None)
    return {
        "id": str(endpoint.id), "asset_id": str(endpoint.asset_id) if endpoint.asset_id else None,
        "source": endpoint.source, "source_agent_id": endpoint.source_agent_id,
        "hostname": endpoint.hostname, "last_seen_at": endpoint.last_seen_at,
        "status": endpoint.status, "open_changes": open_changes,
        "open_incidents": open_incidents,
        "current_snapshot": None if not snapshot else {
            "id": str(snapshot.id), "captured_at": snapshot.captured_at,
            "type": snapshot.snapshot_type, "completeness": snapshot.completeness,
        },
        "hardware_summary": {
            "ram_bytes": sum(_ram_capacity_bytes(item.capacity) or 0 for item in ram),
            "ram_modules": len(ram), "storage_devices": len(storage),
            "cpu": cpu.model if cpu else None,
        },
    }


@router.get("/assets")
def list_assets(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    result = []
    statement = (
        select(AssetRecord, ManagedEndpointRecord, OrganizationRecord.name)
        .outerjoin(ManagedEndpointRecord, ManagedEndpointRecord.asset_id == AssetRecord.id)
        .outerjoin(OrganizationRecord, OrganizationRecord.id == AssetRecord.organization_id)
        .order_by(AssetRecord.inventory_number)
    )
    if principal.organization_id:
        statement = statement.where(AssetRecord.organization_id == principal.organization_id)
    allowed_rooms = permitted_room_ids(session, principal)
    if allowed_rooms is not None:
        statement = statement.where(AssetRecord.room_id.in_(allowed_rooms))
    rows = session.execute(statement).all()
    summaries = _endpoint_summaries(session, [endpoint for _, endpoint, _ in rows if endpoint])
    for asset, endpoint, organization_name in rows:
        view = _asset_view(asset, endpoint.id if endpoint else None, organization_name)
        view["endpoint"] = summaries[endpoint.id] if endpoint else None
        result.append(view)
    return result


@router.get("/assets/export.xlsx")
def export_assets_xlsx(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Assets"
    headers = ["inventory_number", "name", "asset_type", "category", "status", "organization", "building", "floor", "room", "notes", "quantity", "unit", "tracking_mode"]
    sheet.append(headers)
    statement = select(AssetRecord).order_by(AssetRecord.inventory_number)
    if principal.organization_id:
        statement = statement.where(AssetRecord.organization_id == principal.organization_id)
    allowed_rooms = permitted_room_ids(session, principal)
    if allowed_rooms is not None:
        statement = statement.where(AssetRecord.room_id.in_(allowed_rooms))
    for asset in session.scalars(statement):
        organization = session.get(OrganizationRecord, asset.organization_id)
        sheet.append([
            asset.inventory_number, asset.name, asset.asset_type, asset.category, asset.status,
            organization.name if organization else "", asset.building or "", asset.floor or "",
            asset.room or "", asset.notes or "", asset.quantity, asset.unit, asset.tracking_mode,
        ])
    sheet.freeze_panes = "A2"
    for column in sheet.columns:
        letter = column[0].column_letter
        sheet.column_dimensions[letter].width = min(48, max(14, max(len(str(cell.value or "")) for cell in column) + 2))
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="assetguard-assets.xlsx"'},
    )


def _assets_for_principal(session: Session, principal: AuthPrincipal) -> list[tuple[AssetRecord, str]]:
    statement = select(AssetRecord).order_by(AssetRecord.inventory_number)
    if principal.organization_id:
        statement = statement.where(AssetRecord.organization_id == principal.organization_id)
    allowed_rooms = permitted_room_ids(session, principal)
    if allowed_rooms is not None:
        statement = statement.where(AssetRecord.room_id.in_(allowed_rooms))
    result = []
    for asset in session.scalars(statement):
        organization = session.get(OrganizationRecord, asset.organization_id)
        result.append((asset, organization.name if organization else ""))
    return result


def _export_assets_pdf(assets: list[tuple[AssetRecord, str]]) -> BytesIO:
    font = pdf_font_name()
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("AssetGuardTitle", parent=styles["Title"], fontName=font, fontSize=16, leading=20)
    subtitle = ParagraphStyle("AssetGuardSubtitle", parent=styles["Normal"], fontName=font, fontSize=8, leading=11, textColor=colors.HexColor("#4b5563"))
    cell = ParagraphStyle("AssetGuardCell", parent=styles["Normal"], fontName=font, fontSize=7, leading=9)
    header = ParagraphStyle("AssetGuardHeader", parent=cell, textColor=colors.white, alignment=1)
    story = [
        Paragraph("AssetGuard — реестр оборудования", title),
        Paragraph(f"Сформировано: {datetime.now().astimezone().strftime('%d.%m.%Y %H:%M')} · Позиций: {len(assets)}", subtitle),
        Spacer(1, 5 * mm),
    ]
    headings = ["Инв. №", "Наименование", "Тип", "Категория", "Статус", "Организация", "Корпус", "Этаж", "Кабинет", "Примечание"]
    table_data = [[Paragraph(escape(value), header) for value in headings]]
    for asset, organization_name in assets:
        values = [
            asset.inventory_number, asset.name, asset.asset_type, asset.category, asset.status, organization_name,
            asset.building or "", asset.floor or "", asset.room or "", asset.notes or "",
        ]
        table_data.append([Paragraph(escape(str(value)).replace("\n", "<br/>"), cell) for value in values])
    table = Table(table_data, colWidths=[21 * mm, 34 * mm, 19 * mm, 20 * mm, 18 * mm, 29 * mm, 21 * mm, 12 * mm, 17 * mm, 43 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173b69")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(table)
    document.build(story)
    output.seek(0)
    return output


@router.get("/assets/export.pdf")
def export_assets_pdf(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    output = _export_assets_pdf(_assets_for_principal(session, principal))
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="assetguard-assets.pdf"'})


IMPORT_COLUMN_ALIASES = {
    "quantity": {"quantity", "количество", "кол-во"},
    "unit": {"unit", "единица", "единица измерения", "ед. изм.", "ед. изм"},
    "tracking_mode": {"tracking_mode", "tracking mode", "режим учета", "режим учёта"},
    "inventory_number": {"inventory_number", "inventory number", "инвентарный номер", "инв. номер", "инв номер", "инв. №", "инв №", "инвентарный№"},
    "name": {"name", "название", "наименование", "оборудование", "устройство"},
    "asset_type": {"asset_type", "asset type", "тип", "тип оборудования", "вид оборудования"},
    "category": {"category", "категория", "категория имущества"},
    "status": {"status", "статус", "состояние"},
    "organization": {"organization", "организация", "учреждение", "школа"},
    "building": {"building", "корпус", "здание"},
    "floor": {"floor", "этаж"},
    "room": {"room", "кабинет", "аудитория", "помещение"},
    "notes": {"notes", "примечание", "комментарий"},
}


def _normalize_import_header(value: object) -> str:
    return " ".join(str(value).strip().lower().replace("ё", "е").split())


def _canonical_import_columns(header: tuple[object, ...]) -> dict[str, int | None]:
    raw = {_normalize_import_header(value): index for index, value in enumerate(header) if value is not None}
    return {
        field: next((raw[alias] for alias in aliases if alias in raw), None)
        for field, aliases in IMPORT_COLUMN_ALIASES.items()
    }


def _asset_type_from_import(value: str | None) -> str | None:
    if not value:
        return value
    normalized = value.lower().replace("ё", "е").strip()
    canonical_types = {name.lower(): name for name in ("Desktop", "Laptop", "Printer", "Projector", "Network", "Furniture", "Sports", "Educational", "Other")}
    if normalized in canonical_types:
        return canonical_types[normalized]
    if normalized in {"desktop", "пк", "pc", "computer", "workstation", "компьютер", "стационарный", "стационарный компьютер"} or "computer" in normalized or "workstation" in normalized or "компьютер" in normalized or "системный блок" in normalized:
        return "Desktop"
    if normalized in {"laptop", "ноутбук"} or "ноутбук" in normalized:
        return "Laptop"
    if "принтер" in normalized or "мфу" in normalized:
        return "Printer"
    if "проектор" in normalized:
        return "Projector"
    if any(word in normalized for word in ("маршрутизатор", "роутер", "коммутатор", "switch", "router", "точка доступа", "network", "сетев")):
        return "Network"
    if any(word in normalized for word in ("парта", "стол", "стул", "кресло", "шкаф", "мебел", "доска", "тумба", "полка", "furniture", "chair", "desk", "table", "cabinet", "bookcase")):
        return "Furniture"
    if any(word in normalized for word in ("мяч", "ракетка", "скакалка", "обруч", "гантел", "спортинвентар", "спортивн", "sports", "ball", "racket", "rope", "dumbbell", "hoop")):
        return "Sports"
    if any(word in normalized for word in ("микроскоп", "лаборатор", "учебн", "наглядное пособие", "глобус", "телескоп", "educational")):
        return "Educational"
    return "Other" if normalized not in {"other", "прочее", "другое"} else "Other"


def _asset_category_from_import(value: str | None, asset_type: str | None) -> str:
    normalized = (value or "").lower().replace("ё", "е").strip()
    explicit = {
        "it": "IT", "компьютеры и it": "IT", "it-оборудование": "IT", "компьютерное оборудование": "IT",
        "furniture": "FURNITURE", "мебель": "FURNITURE",
        "sports": "SPORTS", "спорт": "SPORTS", "спортинвентарь": "SPORTS", "спортивный инвентарь": "SPORTS",
        "educational": "EDUCATIONAL", "учебное": "EDUCATIONAL", "учебное оборудование": "EDUCATIONAL",
        "other": "OTHER", "прочее": "OTHER", "другое": "OTHER", "другое имущество": "OTHER",
    }
    if normalized in explicit:
        return explicit[normalized]
    return {
        "Desktop": "IT", "Laptop": "IT", "Printer": "IT", "Projector": "IT", "Network": "IT",
        "Furniture": "FURNITURE", "Sports": "SPORTS", "Educational": "EDUCATIONAL", "Other": "OTHER",
    }.get(asset_type or "", "OTHER")


def _import_row_values(row: dict[str, object], row_number: int) -> ImportRow:
    required = ("inventory_number", "name", "asset_type")
    result = {key: (str(row.get(key)).strip() if row.get(key) is not None else None) for key in (
        "inventory_number", "name", "asset_type", "category", "status", "organization", "building", "floor", "room", "notes", "quantity", "unit", "tracking_mode",
    )}
    if any(not result[key] for key in required):
        raise ValueError(f"Строка {row_number}: заполните инвентарный номер, название и тип имущества.")
    result["asset_type"] = _asset_type_from_import(result["asset_type"])
    if result["asset_type"] == "Other":
        name_type = _asset_type_from_import(result["name"])
        if name_type and name_type != "Other":
            result["asset_type"] = name_type
    result["category"] = _asset_category_from_import(result["category"], result["asset_type"])
    if len(result["inventory_number"] or "") > 128 or len(result["name"] or "") > 255:
        raise ValueError(f"Строка {row_number}: инвентарный номер — до 128 символов, название — до 255.")
    quantity = result["quantity"]
    if quantity:
        quantity = re.sub(r"\s+", "", quantity)
        if not re.fullmatch(r"\d+(?:[.,]\d+)?", quantity):
            raise ValueError(f"Строка {row_number}: количество должно быть целым числом от 1 до 1000000.")
        number = Decimal(quantity.replace(",", "."))
        if number != number.to_integral_value() or not 1 <= number <= 1_000_000:
            raise ValueError(f"Строка {row_number}: количество должно быть целым числом от 1 до 1000000; дробный учёт не поддерживается.")
        result["quantity"] = int(number)
    else:
        result["quantity"] = None
    mode = (result["tracking_mode"] or "").upper()
    if mode and mode not in {"INDIVIDUAL", "GROUPED"}:
        raise ValueError(f"Строка {row_number}: режим учёта — INDIVIDUAL или GROUPED.")
    if mode == "INDIVIDUAL" and result["quantity"] not in (None, 1):
        raise ValueError(f"Строка {row_number}: для индивидуального учёта количество должно быть 1.")
    result["tracking_mode"] = mode or None
    if len(result["unit"] or "") > 32:
        raise ValueError(f"Строка {row_number}: единица измерения — до 32 символов.")
    result["unit"] = result["unit"] or None
    return result


def _parse_import_rows(
    header: tuple[object, ...] | list[object], rows: object,
    first_row_number: int = 2, page_number: int | None = None,
) -> list[ImportRow]:
    columns = _canonical_import_columns(tuple(header))
    required_columns = {"inventory_number", "name", "asset_type"}
    if any(columns[column] is None for column in required_columns):
        raise HTTPException(422, "Required columns: inventory_number, name, asset_type (or Russian equivalents).")
    parsed: list[ImportRow] = []
    errors = []
    error_count = 0
    for row_number, values in enumerate(rows, start=first_row_number):
        values = tuple(values or ())
        if not any(value not in (None, "") for value in values):
            continue
        try:
            item = _import_row_values({name: values[index] if index is not None and index < len(values) else None for name, index in columns.items()}, row_number)
        except ValueError as error:
            error_count += 1
            if len(errors) < 50:
                errors.append({"row": row_number, "page": page_number, "message": str(error).partition(": ")[2]})
            continue
        item["_source_row"] = row_number
        item["_source_page"] = page_number
        item["_location_provided"] = any(columns[key] is not None for key in ("building", "floor", "room"))
        parsed.append(item)
    if errors:
        # Reject the whole file before any domain write; never silently skip invalid rows.
        raise HTTPException(422, {"code": "IMPORT_ROWS_INVALID", "message": "Исправьте строки в исходном файле и загрузите его снова.",
                                  "errors": errors, "error_count": error_count})
    return parsed


def _import_assets(
    parsed: list[ImportRow],
    session: Session,
    principal: AuthPrincipal,
    apply: bool,
    source: str,
    excluded_rows: set[int] | None = None,
) -> dict:
    excluded_rows = excluded_rows or set()
    invalid_rows = sorted(index for index in excluded_rows if index < 0 or index >= len(parsed))
    if invalid_rows:
        raise HTTPException(422, "Некорректные номера строк предпросмотра.")
    selected = [(index, item) for index, item in enumerate(parsed) if index not in excluded_rows]
    if apply and not selected:
        raise HTTPException(422, "Выберите хотя бы одну строку для импорта.")
    scoped_organization = session.get(OrganizationRecord, principal.organization_id) if principal.organization_id else None
    if principal.organization_id and not scoped_organization:
        raise HTTPException(403, "The authenticated organization is unavailable.")
    if scoped_organization and any(item.get("organization") not in (None, "", scoped_organization.name) for item in parsed):
        raise HTTPException(403, "A tenant user may import assets only for their organization.")
    try:
        parsed = [{**item, **_import_row_values(item, index + 1), "organization": item.get("organization") or (scoped_organization.name if scoped_organization else "Default Organization")} for index, item in enumerate(parsed)]
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    selected = [(index, item) for index, item in enumerate(parsed) if index not in excluded_rows]
    selected_keys = [(item["organization"], item["inventory_number"]) for _, item in selected]
    if len(selected_keys) != len(set(selected_keys)):
        seen = set()
        errors = []
        error_count = 0
        for index, item in selected:
            key = (item["organization"], item["inventory_number"])
            if key in seen:
                error_count += 1
                if len(errors) < 50:
                    errors.append({"row": item.get("_source_row", index + 1), "page": item.get("_source_page"),
                                   "message": "Инвентарный номер повторяется в этой организации. Исправьте дубли в файле."})
            seen.add(key)
        raise HTTPException(422, {"code": "IMPORT_ROWS_INVALID", "message": "В файле есть повторяющиеся инвентарные номера.",
                                  "errors": errors, "error_count": error_count})
    existing_query = select(AssetRecord, OrganizationRecord.name).join(OrganizationRecord)
    existing_query = existing_query.where(
        AssetRecord.inventory_number.in_({item["inventory_number"] for item in parsed}),
        OrganizationRecord.name.in_({item["organization"] for item in parsed}),
    )
    if scoped_organization:
        existing_query = existing_query.where(AssetRecord.organization_id == scoped_organization.id)
    if apply:
        existing_query = existing_query.with_for_update(of=AssetRecord).execution_options(populate_existing=True)
    existing = {(organization_name, asset.inventory_number): asset for asset, organization_name in session.execute(existing_query)}
    # Accounting acts are authoritative: an old source file must not restore stock,
    # written-off status or the previous room after a move/write-off.
    existing_ids = {asset.id for asset in existing.values()}
    operations = session.execute(select(PhysicalIncidentRecord.asset_id, PhysicalIncidentDecisionRecord.destination_asset_id).join(
        PhysicalIncidentDecisionRecord, PhysicalIncidentDecisionRecord.incident_id == PhysicalIncidentRecord.id,
    ).where(
        PhysicalIncidentDecisionRecord.action.in_({"MOVE", "WRITE_OFF"}),
        or_(PhysicalIncidentRecord.asset_id.in_(existing_ids), PhysicalIncidentDecisionRecord.destination_asset_id.in_(existing_ids)),
    )) if existing_ids else []
    protected_ids = {asset_id for pair in operations for asset_id in pair if asset_id in existing_ids}
    for item in parsed:
        asset = existing.get((item["organization"], item["inventory_number"]))
        item["source_quantity"] = item["quantity"]
        item["accounting_preserved"] = bool(asset and asset.id in protected_ids)
        if item["accounting_preserved"]:
            for key in ("quantity", "unit", "tracking_mode", "status", "building", "floor", "room"):
                item[key] = getattr(asset, key)
        else:
            if asset and not item.get("_location_provided", any(item.get(key) is not None for key in ("building", "floor", "room"))):
                for key in ("building", "floor", "room"):
                    item[key] = getattr(asset, key)
            item["quantity"] = item["quantity"] if item["quantity"] is not None else (asset.quantity if asset else 1)
            item["unit"] = item["unit"] or (asset.unit if asset else "шт.")
            item["tracking_mode"] = item["tracking_mode"] or ("GROUPED" if item["quantity"] > 1 else (asset.tracking_mode if asset else "INDIVIDUAL"))
        if item["tracking_mode"] == "INDIVIDUAL" and item["quantity"] != 1:
            raise HTTPException(422, "INDIVIDUAL assets must have quantity 1.")
        item["quantity_unverified"] = bool(item.get("_quantity_unverified"))
        if item["quantity_unverified"] and asset is None:
            item["quantity"] = None
    if apply and any(item["quantity"] is None for _, item in selected):
        raise HTTPException(422, "Количество в ведомости не распознано. Уточните его в Excel перед импортом новых позиций.")
    actions = [
        "update" if (item["organization"], item["inventory_number"]) in existing else "create"
        for _, item in selected
    ]
    creates = sum(action == "create" for action in actions)
    updates = len(selected) - creates
    if not apply:
        return {
            "rows": len(selected), "total_rows": len(parsed), "creates": creates, "updates": updates, "applied": False,
            "source": source,
            "scope": {"organization_id": str(principal.organization_id) if principal.organization_id else None,
                      "organization_name": scoped_organization.name if scoped_organization else None},
            "samples": [{key: item.get(key) for key in ("inventory_number", "name", "asset_type", "organization", "quantity", "unit", "tracking_mode", "building", "floor", "room")} for item in parsed[:10]],
            "items": [
                {
                    "row": index + 1,
                    "source_row": item.get("_source_row"), "source_page": item.get("_source_page"),
                    "action": "update" if (item["organization"], item["inventory_number"]) in existing else "create",
                    "confidence": item.get("_ocr_confidence"),
                    **{key: item.get(key) for key in ("inventory_number", "name", "asset_type", "organization", "quantity", "unit", "tracking_mode", "source_quantity", "accounting_preserved", "quantity_unverified", "building", "floor", "room")},
                }
                for index, item in enumerate(parsed)
            ],
        }
    now = datetime.now(UTC)
    for _, item in selected:
        organization = scoped_organization or _organization_for_name(session, item["organization"])
        asset = existing.get((organization.name, item["inventory_number"]))
        imported_category = item.get("category") or _asset_category_from_import(None, item.get("asset_type"))
        if asset is None:
            asset = AssetRecord(organization_id=organization.id, inventory_number=item["inventory_number"] or "", name=item["name"] or "", asset_type=item["asset_type"] or "Other", category=imported_category, quantity=item["quantity"], unit=item["unit"], tracking_mode=item["tracking_mode"], status=item["status"] or "ACTIVE", building=item["building"], floor=item["floor"], room=item["room"], notes=item["notes"], created_at=now, updated_at=now)
            session.add(asset); session.flush()
            append_asset_history(session, asset_id=asset.id, event_type="ASSET_CREATED", related_entity_type="Asset", related_entity_id=asset.id, message=f"Asset imported from {source}.", metadata={"inventory_number": asset.inventory_number, "source": source})
        else:
            for key in ("name", "asset_type", "building", "floor", "room", "notes", "quantity", "unit", "tracking_mode"):
                setattr(asset, key, item[key])
            asset.category = imported_category
            if item["status"]:
                asset.status = item["status"]
            asset.updated_at = now
            append_asset_history(session, asset_id=asset.id, event_type="ASSET_UPDATED", related_entity_type="Asset", related_entity_id=asset.id, message=f"Asset imported from {source}.", metadata={"source": source})
        # Imported locations must be canonical so the same assets can be inspected in the room UI.
        if asset.room:
            _ensure_room_for_legacy_location(asset, session)
        else:
            asset.room_id = None
    session.commit()
    return {"rows": len(selected), "creates": creates, "updates": updates, "applied": True}


def _government_inventory_rows(table: list[list[str | None]], filename: str | None, page_number: int | None = None) -> list[ImportRow]:
    """Map the standard Kazakhstan accounting inventory statement to AssetGuard rows.

    A statement row can describe several identical items. It becomes one grouped AssetGuard
    record, while the original quantity, price and accounting number remain in its notes.
    """
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(filename or "inventory").stem).strip("-") or "inventory"
    parsed: list[ImportRow] = []
    for row in table:
        values = [str(value or "").strip() for value in row]
        if len(values) < 9 or not re.fullmatch(r"\d+", values[0]):
            continue
        # The official form repeats the sequence number in the last column. This prevents
        # captions, page footers and multi-row headers from being treated as equipment.
        if values[-1] and values[-1] != values[0]:
            continue
        name = values[1]
        if not name or "\ufffd" in name:
            continue
        accounting_number, unit, price, quantity, total = values[2], values[3], values[4], values[7], values[8]
        notes = [f"Импорт из инвентаризационной ведомости: {filename or 'PDF'}."]
        if accounting_number:
            notes.append(f"Номенклатурный номер: {accounting_number}.")
        if quantity:
            notes.append(f"Количество по ведомости: {quantity} {unit or 'шт.'}.")
        if price:
            notes.append(f"Цена: {price} тг.")
        if total:
            notes.append(f"Сумма: {total} тг.")
        parsed.append({
            "inventory_number": f"PDF-{safe_stem}-{values[0]}" if page_number is None else f"PDF-{safe_stem}-P{page_number}-{values[0]}",
            "name": name,
            "asset_type": _asset_type_from_import(name),
            "status": "ACTIVE",
            "quantity": quantity or None, "unit": unit or None, "tracking_mode": "GROUPED",
            "_quantity_unverified": not bool(quantity),
            "organization": None, "building": None, "floor": None, "room": None,
            "notes": " ".join(notes),
        })
    return parsed


def _ocr_government_inventory_pdf(content: bytes, filename: str | None) -> list[ImportRow]:
    """OCR only strict itemized rows: a repeated row number must bracket a readable name."""
    try:
        import pypdfium2 as pdfium
        import pytesseract
        from pytesseract import Output
    except ImportError as error:
        raise RuntimeError("Для OCR установите runtime-компоненты AssetGuard: pypdfium2, pytesseract и Tesseract OCR с языками rus/kaz/eng.") from error

    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(filename or "inventory").stem).strip("-") or "inventory"
    tesseract_cmd = get_settings().tesseract_cmd
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    units = {"шт", "шт.", "штук", "компл", "компл.", "комплект", "кг", "м", "м2", "л", "упак", "пара"}
    parsed: list[ImportRow] = []
    try:
        document = pdfium.PdfDocument(content)
        if len(document) > 30:
            raise ValueError("Сканированный PDF превышает лимит OCR: не более 30 страниц за импорт.")
        ocr_config = "--psm 6"
        tessdata_dir = get_settings().tesseract_data_dir
        if tessdata_dir:
            ocr_config += f" --tessdata-dir {tessdata_dir}"
        for page_index in range(len(document)):
            image = document[page_index].render(scale=2).to_pil()
            data = pytesseract.image_to_data(image, lang="rus+kaz+eng", config=ocr_config, output_type=Output.DICT)
            lines: dict[tuple[int, int, int, int], list[tuple[int, str, float]]] = {}
            for index, raw_text in enumerate(data["text"]):
                word = str(raw_text).strip()
                try:
                    confidence = float(data["conf"][index])
                except (TypeError, ValueError):
                    continue
                if not word or confidence < 45:
                    continue
                key = (data["page_num"][index], data["block_num"][index], data["par_num"][index], data["line_num"][index])
                lines.setdefault(key, []).append((int(data["left"][index]), word, confidence))
            seen_sequences: set[str] = set()
            for words in lines.values():
                words.sort(key=lambda item: item[0])
                tokens = [word for _, word, _ in words]
                if len(tokens) < 4 or not re.fullmatch(r"\d{1,4}", tokens[0]) or tokens[-1] != tokens[0]:
                    continue
                confidence = sum(value for _, _, value in words) / len(words)
                if confidence < 70 or tokens[0] in seen_sequences:
                    continue
                seen_sequences.add(tokens[0])
                middle = tokens[1:-1]
                metadata_index = next((i for i, token in enumerate(middle) if re.fullmatch(r"\d{5,}", token)), None)
                if metadata_index is None:
                    metadata_index = next((i for i, token in enumerate(middle) if token.lower().strip(".,") in units), None)
                if metadata_index is None:
                    # Without a recognizable accounting number or unit boundary we cannot
                    # separate the item name from neighboring table columns safely.
                    continue
                name = " ".join(middle[:metadata_index]).strip(" .,:;|-")
                if len(re.findall(r"[A-Za-zА-Яа-яӘәҒғҚқҢңӨөҰұҮүҺһІі]", name)) < 3:
                    continue
                inventory_number = f"PDF-{safe_stem}-P{page_index + 1}-{tokens[0]}"
                unit_index = next((i for i, token in enumerate(middle) if token.lower().strip(".,") in units), None)
                numeric_tail = middle[unit_index + 1:] if unit_index is not None else []
                # Accept only the complete standard price/count/total tail. OCR loses
                # column boundaries; guessing a missing count would corrupt stock.
                recognized_quantity = numeric_tail[-2] if len(numeric_tail) in {3, 5} and all(
                    re.fullmatch(r"\d+(?:[.,]\d+)?", token) for token in numeric_tail
                ) else None
                parsed.append({
                    "inventory_number": inventory_number, "name": name,
                    "asset_type": _asset_type_from_import(name), "status": "ACTIVE",
                    "organization": None, "building": None, "floor": None, "room": None,
                    "notes": f"Распознано OCR из скана ({round(confidence)}%); сверьте с оригиналом перед использованием.",
                    "_ocr_confidence": round(confidence),
                    "quantity": recognized_quantity,
                    "unit": middle[unit_index] if unit_index is not None else None,
                    "tracking_mode": "GROUPED", "_quantity_unverified": recognized_quantity is None,
                })
    except ValueError:
        raise
    except Exception as error:
        if error.__class__.__name__ in {"TesseractNotFoundError", "TesseractError"}:
            raise RuntimeError("OCR не запущен: установите Tesseract OCR и языковые пакеты rus, kaz и eng.") from error
        if isinstance(error, UnicodeDecodeError):
            raise RuntimeError("OCR в Windows требует ASCII-путь во временном каталоге и каталоге языковых моделей. Укажите ASSETGUARD_OCR_TEMP_DIR и ASSETGUARD_TESSDATA_DIR, затем перезапустите API.") from error
        raise RuntimeError("Не удалось выполнить OCR этого PDF. Проверьте файл и доступность Tesseract OCR.") from error
    return parsed


@router.post("/assets/import.xlsx")
def import_assets_xlsx(
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_admin)],
    apply: bool = Query(default=False),
    exclude_row: list[int] = Form(default=[]),
):
    if file.content_type not in {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    } and not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(415, "Upload an .xlsx file.")
    try:
        content = file.file.read(5 * 1024 * 1024 + 1)
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(413, "Excel-файл должен быть не больше 5 МБ.")
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(422, "The uploaded file is not a valid .xlsx workbook.") from error
    try:
        rows = workbook.active.iter_rows(values_only=True)
        header = next(rows, None)
        if not header:
            raise HTTPException(422, "The workbook is empty.")
        return _import_assets(_parse_import_rows(header, rows), session, principal, apply, "xlsx", set(exclude_row if isinstance(exclude_row, list) else []))
    finally:
        workbook.close()


@router.post("/assets/import.pdf")
def import_assets_pdf(
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_admin)],
    apply: bool = Query(default=False),
    exclude_row: list[int] = Form(default=[]),
):
    if file.content_type not in {"application/pdf", "application/octet-stream"} and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(415, "Upload a .pdf file.")
    content = file.file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "The PDF must be no larger than 10 MB.")
    try:
        with pdfplumber.open(BytesIO(content)) as document:
            pages = [(page_number, [table for table in page.extract_tables() if table]) for page_number, page in enumerate(document.pages, start=1)]
    except Exception as error:
        raise HTTPException(422, "The uploaded file is not a valid readable PDF.") from error
    generic_rows: list[ImportRow] = []
    government_rows: list[ImportRow] = []
    for page_number, tables in pages:
        for table in tables:
            header, *rows = table
            if header:
                try:
                    generic_rows.extend(_parse_import_rows(header, rows, page_number=page_number))
                except HTTPException as error:
                    if error.status_code != 422 or not isinstance(error.detail, str) or not error.detail.startswith("Required columns"):
                        raise
            government_rows.extend(_government_inventory_rows(table, file.filename, page_number))
    if generic_rows:
        return _import_assets(generic_rows, session, principal, apply, "pdf", set(exclude_row if isinstance(exclude_row, list) else []))
    if government_rows:
        deduplicated = {(item.get("organization"), item["inventory_number"]): item for item in government_rows}
        return _import_assets(list(deduplicated.values()), session, principal, apply, "government PDF inventory statement", set(exclude_row if isinstance(exclude_row, list) else []))
    try:
        ocr_rows = _ocr_government_inventory_pdf(content, file.filename)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if ocr_rows:
        return _import_assets(ocr_rows, session, principal, apply, "OCR government PDF inventory statement", set(exclude_row if isinstance(exclude_row, list) else []))
    raise HTTPException(422, "Не найдена поддерживаемая ведомость с построчными данными. Пустой бланк и сводное поле без отдельных позиций не импортируются; для скана нужны читаемые строки ведомости.")


@router.get("/assets/{asset_id}/qr.svg")
def asset_qr_svg(
    asset_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_viewer)],
    public_url: str | None = Query(default=None, max_length=2048),
):
    asset = _scoped_asset(session, asset_id, principal)
    base_url = qr_base_url(public_url)
    payload = f"{base_url}/#asset={asset.id}"
    return qr_svg_response(payload, f"AssetGuard {asset.inventory_number}")


@router.post("/assets", status_code=status.HTTP_201_CREATED)
def create_asset(body: AssetCreate, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    organization = session.get(OrganizationRecord, principal.organization_id) if principal.organization_id else session.scalar(select(OrganizationRecord).order_by(OrganizationRecord.created_at))
    if not organization:
        organization = OrganizationRecord(name="Default Organization", created_at=datetime.now(UTC))
        session.add(organization)
        session.flush()
    if session.scalar(select(AssetRecord).where(
        AssetRecord.organization_id == organization.id,
        AssetRecord.inventory_number == body.inventory_number,
    )):
        raise HTTPException(status.HTTP_409_CONFLICT, "Inventory number already exists.")
    now = datetime.now(UTC)
    asset = AssetRecord(
        organization_id=organization.id, inventory_number=body.inventory_number,
        name=body.name, asset_type=body.asset_type, category=body.category, tracking_mode=body.tracking_mode, quantity=body.quantity, unit=body.unit.strip(), status=body.status,
        building=body.building, floor=body.floor, room=body.room, notes=body.notes,
        created_at=now, updated_at=now,
    )
    _apply_room_location(asset, body.room_id, session, organization.id)
    if body.room_id is None:
        _ensure_room_for_legacy_location(asset, session)
    require_room_access(session, asset.room_id, principal, write=True)
    session.add(asset)
    session.flush()
    append_asset_history(
        session, asset_id=asset.id, event_type="ASSET_CREATED",
        related_entity_type="Asset", related_entity_id=asset.id,
        message="Asset created.", metadata={"inventory_number": asset.inventory_number},
    )
    session.commit()
    session.refresh(asset)
    return _asset_view(asset, None, organization.name)


@router.patch("/assets/{asset_id}")
def update_asset(asset_id: UUID, body: AssetUpdate, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    asset = _scoped_asset(session, asset_id, principal)
    require_room_access(session, asset.room_id, principal, write=True)
    changes = body.model_dump(exclude_unset=True)
    if "inventory_number" in changes:
        duplicate = session.scalar(select(AssetRecord).where(
            AssetRecord.organization_id == asset.organization_id,
            AssetRecord.inventory_number == changes["inventory_number"],
            AssetRecord.id != asset.id,
        ))
        if duplicate:
            raise HTTPException(409, "Inventory number already exists.")
    if "room_id" in changes:
        _apply_room_location(asset, changes.pop("room_id"), session, asset.organization_id)
    for field, value in changes.items():
        setattr(asset, field, value)
    if "room_id" not in body.model_fields_set and {"building", "floor", "room"} & set(changes):
        _ensure_room_for_legacy_location(asset, session)
    require_room_access(session, asset.room_id, principal, write=True)
    asset.updated_at = datetime.now(UTC)
    append_asset_history(
        session, asset_id=asset.id, event_type="ASSET_UPDATED",
        related_entity_type="Asset", related_entity_id=asset.id,
        message="Asset details updated.", metadata={"fields": sorted(changes)},
    )
    session.commit()
    endpoint_id = session.scalar(select(ManagedEndpointRecord.id).where(ManagedEndpointRecord.asset_id == asset.id))
    organization = session.get(OrganizationRecord, asset.organization_id)
    return _asset_view(asset, endpoint_id, organization.name if organization else None)


@router.get("/endpoints")
def list_endpoints(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    result = []
    statement = (
        select(ManagedEndpointRecord, AssetRecord, OrganizationRecord.name)
        .outerjoin(AssetRecord, AssetRecord.id == ManagedEndpointRecord.asset_id)
        .outerjoin(OrganizationRecord, OrganizationRecord.id == AssetRecord.organization_id)
        .order_by(ManagedEndpointRecord.last_seen_at.desc())
    )
    if principal.organization_id:
        statement = statement.where(ManagedEndpointRecord.organization_id == principal.organization_id)
    allowed_rooms = permitted_room_ids(session, principal)
    if allowed_rooms is not None:
        statement = statement.where(AssetRecord.room_id.in_(allowed_rooms))
    rows = session.execute(statement).all()
    summaries = _endpoint_summaries(session, [endpoint for endpoint, _, _ in rows])
    for endpoint, asset, organization_name in rows:
        item = summaries[endpoint.id]
        item["asset"] = None if not asset else _asset_view(asset, endpoint.id, organization_name)
        result.append(item)
    return result


@router.post("/maintenance/evaluate-endpoints", dependencies=[Depends(require_admin)])
def evaluate_endpoints(session: Annotated[Session, Depends(get_session)]):
    changed = evaluate_last_seen(session, get_settings().endpoint_stale_after_hours)
    return {"updated": changed, "stale_after_hours": get_settings().endpoint_stale_after_hours}


@router.get("/endpoints/{endpoint_id}")
def endpoint_detail(endpoint_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    endpoint = scoped_endpoint(session, endpoint_id, principal)
    identifiers = list(session.scalars(select(EndpointIdentifierRecord).where(
        EndpointIdentifierRecord.managed_endpoint_id == endpoint.id,
    ).order_by(EndpointIdentifierRecord.identifier_type)))
    snapshots = list(session.scalars(select(HardwareSnapshotRecord).where(
        HardwareSnapshotRecord.managed_endpoint_id == endpoint.id,
    ).order_by(HardwareSnapshotRecord.captured_at.desc())))
    return {
        "id": str(endpoint.id), "asset_id": str(endpoint.asset_id) if endpoint.asset_id else None,
        "source": endpoint.source, "source_agent_id": endpoint.source_agent_id,
        "hostname": endpoint.hostname, "last_seen_at": endpoint.last_seen_at,
        "status": endpoint.status,
        "identifiers": [{
            "type": item.identifier_type, "value": item.raw_value,
            "confidence": item.confidence, "first_seen_at": item.first_seen_at,
            "last_seen_at": item.last_seen_at, "active": item.is_active,
        } for item in identifiers],
        "snapshot_count": len(snapshots),
        "current_snapshot_id": str(snapshots[0].id) if snapshots else None,
    }


@router.post("/endpoints/{endpoint_id}/asset/{asset_id}")
def link_endpoint(
    endpoint_id: UUID,
    asset_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_admin)],
):
    endpoint = session.get(ManagedEndpointRecord, endpoint_id)
    asset = session.get(AssetRecord, asset_id)
    if not endpoint or not asset or (principal.organization_id and (
        endpoint.organization_id != principal.organization_id or asset.organization_id != principal.organization_id
    )):
        raise HTTPException(404, "Asset or endpoint was not found.")
    if endpoint.organization_id and asset.organization_id and endpoint.organization_id != asset.organization_id:
        raise HTTPException(409, "An endpoint and an asset must belong to the same organization.")
    if asset.tracking_mode != "INDIVIDUAL" or asset.category != "IT":
        raise HTTPException(422, "Only individually tracked IT assets can be linked to an Agent endpoint.")
    endpoint.organization_id = endpoint.organization_id or asset.organization_id
    if endpoint.asset_id and endpoint.asset_id != asset.id:
        append_asset_history(
            session, asset_id=endpoint.asset_id, endpoint_id=endpoint.id,
            event_type="ENDPOINT_UNLINKED", related_entity_type="ManagedEndpoint",
            related_entity_id=endpoint.id, message="Endpoint unlinked from asset.",
        )
    for prior in session.scalars(select(ManagedEndpointRecord).where(
        ManagedEndpointRecord.asset_id == asset.id, ManagedEndpointRecord.id != endpoint.id,
    )):
        append_asset_history(
            session, asset_id=asset.id, endpoint_id=prior.id,
            event_type="ENDPOINT_UNLINKED", related_entity_type="ManagedEndpoint",
            related_entity_id=prior.id, message="Previous endpoint unlinked from asset.",
        )
        prior.asset_id = None
        prior.updated_at = datetime.now(UTC)
    endpoint.asset_id = asset.id
    endpoint.updated_at = datetime.now(UTC)
    append_asset_history(
        session, asset_id=asset.id, endpoint_id=endpoint.id,
        event_type="ENDPOINT_LINKED", related_entity_type="ManagedEndpoint",
        related_entity_id=endpoint.id, message="Endpoint linked to asset.",
        metadata={"hostname": endpoint.hostname},
    )
    session.commit()
    return {"status": "linked"}


def _components(session: Session, snapshot: HardwareSnapshotRecord | None) -> list[dict]:
    if not snapshot:
        return []
    return [_component_view(item) for item in session.scalars(select(ComponentObservationRecord).where(
        ComponentObservationRecord.hardware_snapshot_id == snapshot.id,
    ))]


def _installer_version(content: dict) -> str | None:
    """Read the version tag written by the AssetGuard installer from GLPI inventory."""
    tags = content.get("tag")
    values = list(tags) if isinstance(tags, list) else [tags]
    # Local GLPI XML writes tags as ACCOUNTINFO, unlike the JSON bridge.
    account_info = content.get("accountinfo")
    entries = account_info if isinstance(account_info, list) else [account_info]
    for entry in entries:
        if isinstance(entry, dict) and str(entry.get("keyname", "")).upper() == "TAG":
            values.append(entry.get("keyvalue"))
    for value in values:
        if isinstance(value, str) and value.startswith(ASSETGUARD_INSTALLER_TAG_PREFIX):
            version = value.removeprefix(ASSETGUARD_INSTALLER_TAG_PREFIX).strip()
            if version and len(version) <= 32:
                return version
    return None


def _agent_version_status(version: str | None) -> str:
    if not version:
        return "UNKNOWN"
    return "SUPPORTED" if version in SUPPORTED_AGENT_VERSIONS else "UNSUPPORTED"


def _system_sections(
    session: Session, endpoint: ManagedEndpointRecord, snapshot: HardwareSnapshotRecord | None,
) -> tuple[dict, dict | None]:
    if not snapshot:
        return {}, None
    latest_raw = session.get(RawInventoryRecord, snapshot.raw_inventory_id)
    if not latest_raw:
        return {}, None
    inventories = list(session.scalars(select(RawInventoryRecord).where(
        RawInventoryRecord.managed_endpoint_id == endpoint.id,
        RawInventoryRecord.processing_status == "PROCESSED",
    ).order_by(RawInventoryRecord.received_at.desc()).limit(50)))
    merged_objects = {"hardware": {}, "bios": {}, "operatingsystem": {}, "assetguard_network": {}}
    latest_lists = {"drives": [], "controllers": []}
    installer_version = None
    for inventory in inventories:
        content = inventory.payload.get("content") if isinstance(inventory.payload, dict) else None
        if not isinstance(content, dict):
            continue
        if installer_version is None:
            installer_version = _installer_version(content)
        for section in merged_objects:
            value = content.get(section)
            if isinstance(value, dict):
                for key, item in value.items():
                    if key not in merged_objects[section] and item not in (None, ""):
                        merged_objects[section][key] = item
        for section in latest_lists:
            value = content.get(section)
            if not latest_lists[section] and isinstance(value, list) and value:
                latest_lists[section] = value
    hardware = merged_objects["hardware"]
    # Windows product keys/owner fields remain evidence-only and are never exposed to the dashboard.
    safe_hardware = {key: hardware.get(key) for key in (
        "name", "uuid", "chassis_type", "memory", "workgroup", "winlang", "vmsystem",
    ) if hardware.get(key) not in (None, "")}
    return {
        "hardware": safe_hardware,
        "bios": merged_objects["bios"],
        "operating_system": merged_objects["operatingsystem"],
        "network_quality": merged_objects["assetguard_network"],
        "drives": latest_lists["drives"],
        "controllers": latest_lists["controllers"],
    }, {
        "id": str(latest_raw.id), "received_at": latest_raw.received_at, "source": latest_raw.source,
        "source_version": latest_raw.source_version, "type": latest_raw.inventory_type,
        "processing_status": latest_raw.processing_status,
        "installer_version": installer_version,
        "agent_version_status": _agent_version_status(latest_raw.source_version),
        "supported_agent_versions": sorted(SUPPORTED_AGENT_VERSIONS),
    }


@router.get("/assets/{asset_id}")
def asset_detail(asset_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    asset = _scoped_asset(session, asset_id, principal)
    endpoint = session.scalar(select(ManagedEndpointRecord).where(ManagedEndpointRecord.asset_id == asset.id))
    organization = session.get(OrganizationRecord, asset.organization_id)
    result = _asset_view(asset, endpoint.id if endpoint else None, organization.name if organization else None)
    result.update({
        "endpoint": None, "current_snapshot_id": None, "baseline_snapshot_id": None,
        "current_hardware": [], "baseline_hardware": [], "changes": [], "incidents": [],
        "system": {}, "latest_inventory": None,
        "history": [{
            "id": str(item.id), "type": item.event_type, "occurred_at": item.occurred_at,
            "message": item.message, "metadata": item.metadata_json,
        } for item in session.scalars(select(AssetHistoryEntryRecord).where(
            AssetHistoryEntryRecord.asset_id == asset.id,
        ).order_by(AssetHistoryEntryRecord.occurred_at.desc()))],
    })
    if not endpoint:
        return result
    snapshots = list(session.scalars(select(HardwareSnapshotRecord).where(
        HardwareSnapshotRecord.managed_endpoint_id == endpoint.id,
    ).order_by(HardwareSnapshotRecord.captured_at.desc())))
    current = snapshots[0] if snapshots else None
    baseline = session.scalar(select(BaselineRecord).where(
        BaselineRecord.managed_endpoint_id == endpoint.id, BaselineRecord.status == "ACTIVE",
    ))
    baseline_snapshot = session.get(HardwareSnapshotRecord, baseline.hardware_snapshot_id) if baseline else None
    identifiers = list(session.scalars(select(EndpointIdentifierRecord).where(
        EndpointIdentifierRecord.managed_endpoint_id == endpoint.id,
        EndpointIdentifierRecord.is_active.is_(True),
    ).order_by(EndpointIdentifierRecord.identifier_type)))
    observed_snapshot = _latest_observed_snapshot(session, endpoint.id)
    system, latest_inventory = _system_sections(session, endpoint, current)
    result.update({
        "endpoint": {
            **_endpoint_summary(session, endpoint),
            "identifiers": [{
                "type": item.identifier_type, "value": item.raw_value,
                "confidence": item.confidence,
            } for item in identifiers],
        },
        "current_snapshot_id": str(current.id) if current else None,
        "recommended_baseline_snapshot_id": str(observed_snapshot.id) if observed_snapshot else None,
        "baseline_snapshot_id": str(baseline_snapshot.id) if baseline_snapshot else None,
        "current_snapshot": None if not current else {
            "id": str(current.id), "captured_at": current.captured_at,
            "type": current.snapshot_type, "completeness": current.completeness,
        },
        "baseline": None if not baseline else {
            "id": str(baseline.id), "snapshot_id": str(baseline.hardware_snapshot_id),
            "accepted_at": baseline.accepted_at, "reason": baseline.reason,
        },
        "current_hardware": [_component_view(item) for item in _latest_components(session, endpoint.id)],
        "baseline_hardware": _components(session, baseline_snapshot),
        "system": system, "latest_inventory": latest_inventory,
        "changes": [{
            "id": str(item.id), "type": item.event_type,
            "component_type": item.component_type, "confidence": item.confidence,
            "severity": item.severity, "status": item.status,
            "evidence": item.evidence, "detected_at": item.detected_at,
        } for item in session.scalars(select(ChangeEventRecord).where(
            ChangeEventRecord.managed_endpoint_id == endpoint.id,
        ).order_by(ChangeEventRecord.detected_at.desc()))],
        "incidents": [{
            "id": str(item.id), "title": item.title, "status": item.status,
            "severity": item.severity, "created_at": item.created_at,
        } for item in session.scalars(select(IncidentRecord).where(
            IncidentRecord.managed_endpoint_id == endpoint.id,
        ).order_by(IncidentRecord.created_at.desc()))],
    })
    return result
