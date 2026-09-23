from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session
from assetguard.modules.assets.models import AssetRecord, OrganizationRecord
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.history.service import append_asset_history
from assetguard.modules.endpoints.service import evaluate_last_seen
from assetguard.modules.incidents.models import AssetHistoryEntryRecord, IncidentRecord
from assetguard.modules.identity.auth import AuthPrincipal, session_principal
from assetguard.modules.snapshots.models import (
    ComponentObservationRecord, EndpointIdentifierRecord,
    HardwareSnapshotRecord, ManagedEndpointRecord,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(
    token: Annotated[str | None, Header(alias="X-AssetGuard-Admin-Token")] = None,
    session: Session = Depends(get_session),
) -> AuthPrincipal:
    settings = get_settings()
    valid = [settings.admin_shared_secret, settings.previous_admin_shared_secret]
    shared = bool(token and any(candidate and secrets.compare_digest(token, candidate) for candidate in valid))
    if shared:
        return AuthPrincipal(username="bootstrap-admin", role="ADMIN", session_id=None)
    principal = session_principal(session, token) if token else None
    if not principal or principal.role != "ADMIN":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid administrator credentials.")
    return principal


def require_viewer(
    token: Annotated[str | None, Header(alias="X-AssetGuard-Admin-Token")] = None,
    session: Session = Depends(get_session),
) -> AuthPrincipal:
    settings = get_settings()
    valid = [settings.admin_shared_secret, settings.previous_admin_shared_secret, settings.viewer_shared_secret]
    if token and any(candidate and secrets.compare_digest(token, candidate) for candidate in valid):
        role = "VIEWER" if settings.viewer_shared_secret and secrets.compare_digest(token, settings.viewer_shared_secret) else "ADMIN"
        return AuthPrincipal(username=f"shared-{role.lower()}", role=role, session_id=None)
    principal = session_principal(session, token) if token else None
    if not principal or principal.role not in {"ADMIN", "VIEWER"}:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid AssetGuard credentials.")
    return principal


class AssetCreate(BaseModel):
    inventory_number: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    asset_type: Literal["Desktop", "Laptop", "Other"]
    status: str = Field(default="ACTIVE", max_length=32)
    room: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class AssetUpdate(BaseModel):
    inventory_number: str | None = Field(default=None, min_length=1, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_type: Literal["Desktop", "Laptop", "Other"] | None = None
    status: str | None = Field(default=None, max_length=32)
    room: str | None = Field(default=None, max_length=255)
    notes: str | None = None


def _asset_view(asset: AssetRecord, endpoint_id: UUID | None) -> dict:
    return {
        "id": str(asset.id), "inventory_number": asset.inventory_number,
        "name": asset.name, "asset_type": asset.asset_type, "status": asset.status,
        "room": asset.room, "notes": asset.notes,
        "endpoint_id": str(endpoint_id) if endpoint_id else None,
    }


@router.get("/assets", dependencies=[Depends(require_viewer)])
def list_assets(session: Annotated[Session, Depends(get_session)]):
    return [
        _asset_view(asset, session.scalar(select(ManagedEndpointRecord.id).where(ManagedEndpointRecord.asset_id == asset.id)))
        for asset in session.scalars(select(AssetRecord).order_by(AssetRecord.inventory_number))
    ]


@router.post("/assets", dependencies=[Depends(require_admin)], status_code=status.HTTP_201_CREATED)
def create_asset(body: AssetCreate, session: Annotated[Session, Depends(get_session)]):
    organization = session.scalar(select(OrganizationRecord).order_by(OrganizationRecord.created_at))
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
        name=body.name, asset_type=body.asset_type, status=body.status,
        room=body.room, notes=body.notes, created_at=now, updated_at=now,
    )
    session.add(asset)
    session.flush()
    append_asset_history(
        session, asset_id=asset.id, event_type="ASSET_CREATED",
        related_entity_type="Asset", related_entity_id=asset.id,
        message="Asset created.", metadata={"inventory_number": asset.inventory_number},
    )
    session.commit()
    session.refresh(asset)
    return _asset_view(asset, None)


@router.patch("/assets/{asset_id}", dependencies=[Depends(require_admin)])
def update_asset(asset_id: UUID, body: AssetUpdate, session: Annotated[Session, Depends(get_session)]):
    asset = session.get(AssetRecord, asset_id)
    if not asset:
        raise HTTPException(404, "Asset was not found.")
    changes = body.model_dump(exclude_unset=True)
    if "inventory_number" in changes:
        duplicate = session.scalar(select(AssetRecord).where(
            AssetRecord.organization_id == asset.organization_id,
            AssetRecord.inventory_number == changes["inventory_number"],
            AssetRecord.id != asset.id,
        ))
        if duplicate:
            raise HTTPException(409, "Inventory number already exists.")
    for field, value in changes.items():
        setattr(asset, field, value)
    asset.updated_at = datetime.now(UTC)
    append_asset_history(
        session, asset_id=asset.id, event_type="ASSET_UPDATED",
        related_entity_type="Asset", related_entity_id=asset.id,
        message="Asset details updated.", metadata={"fields": sorted(changes)},
    )
    session.commit()
    endpoint_id = session.scalar(select(ManagedEndpointRecord.id).where(ManagedEndpointRecord.asset_id == asset.id))
    return _asset_view(asset, endpoint_id)


@router.get("/endpoints", dependencies=[Depends(require_viewer)])
def list_endpoints(session: Annotated[Session, Depends(get_session)]):
    result = []
    for endpoint in session.scalars(select(ManagedEndpointRecord).order_by(ManagedEndpointRecord.last_seen_at.desc())):
        result.append({
            "id": str(endpoint.id), "asset_id": str(endpoint.asset_id) if endpoint.asset_id else None,
            "source": endpoint.source, "source_agent_id": endpoint.source_agent_id,
            "hostname": endpoint.hostname, "last_seen_at": endpoint.last_seen_at,
            "status": endpoint.status,
        })
    return result


@router.post("/maintenance/evaluate-endpoints", dependencies=[Depends(require_admin)])
def evaluate_endpoints(session: Annotated[Session, Depends(get_session)]):
    changed = evaluate_last_seen(session, get_settings().endpoint_stale_after_hours)
    return {"updated": changed, "stale_after_hours": get_settings().endpoint_stale_after_hours}


@router.get("/endpoints/{endpoint_id}", dependencies=[Depends(require_viewer)])
def endpoint_detail(endpoint_id: UUID, session: Annotated[Session, Depends(get_session)]):
    endpoint = session.get(ManagedEndpointRecord, endpoint_id)
    if not endpoint:
        raise HTTPException(404, "Endpoint was not found.")
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


@router.post("/endpoints/{endpoint_id}/asset/{asset_id}", dependencies=[Depends(require_admin)])
def link_endpoint(endpoint_id: UUID, asset_id: UUID, session: Annotated[Session, Depends(get_session)]):
    endpoint = session.get(ManagedEndpointRecord, endpoint_id)
    asset = session.get(AssetRecord, asset_id)
    if not endpoint or not asset:
        raise HTTPException(404, "Asset or endpoint was not found.")
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
    return [{
        "type": item.component_type, "model": item.model, "serial": item.serial_number,
        "capacity": item.capacity, "slot": item.slot, "confidence": item.confidence,
    } for item in session.scalars(select(ComponentObservationRecord).where(
        ComponentObservationRecord.hardware_snapshot_id == snapshot.id,
    ))]


@router.get("/assets/{asset_id}", dependencies=[Depends(require_viewer)])
def asset_detail(asset_id: UUID, session: Annotated[Session, Depends(get_session)]):
    asset = session.get(AssetRecord, asset_id)
    if not asset:
        raise HTTPException(404, "Asset was not found.")
    endpoint = session.scalar(select(ManagedEndpointRecord).where(ManagedEndpointRecord.asset_id == asset.id))
    result = _asset_view(asset, endpoint.id if endpoint else None)
    result.update({
        "endpoint": None, "current_snapshot_id": None, "baseline_snapshot_id": None,
        "current_hardware": [], "baseline_hardware": [], "changes": [], "incidents": [],
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
    result.update({
        "endpoint": {
            "id": str(endpoint.id), "hostname": endpoint.hostname,
            "status": endpoint.status, "last_seen_at": endpoint.last_seen_at,
        },
        "current_snapshot_id": str(current.id) if current else None,
        "baseline_snapshot_id": str(baseline_snapshot.id) if baseline_snapshot else None,
        "current_hardware": _components(session, current),
        "baseline_hardware": _components(session, baseline_snapshot),
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
