from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.admin_assets import require_admin, require_viewer, scoped_endpoint
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.baselines.service import accept_snapshot_as_baseline
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.incidents.models import (
    EndpointHistoryEntryRecord, IncidentDecisionRecord, IncidentRecord,
)
from assetguard.modules.incidents.service import decide_incident
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.identity.location_access import permitted_room_ids
from assetguard.modules.assets.models import AssetRecord
from assetguard.modules.snapshots.models import ComponentObservationRecord, HardwareSnapshotRecord, ManagedEndpointRecord

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_viewer)])
Classification = Literal[
    "PLANNED_MAINTENANCE", "UPGRADE", "REPAIR", "AUTHORIZED_CHANGE",
    "COMPONENT_TRANSFER", "UNKNOWN", "REQUIRES_INVESTIGATION", "FALSE_POSITIVE",
]


class BaselineAccept(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class DecisionBody(BaseModel):
    classification: Classification
    comment: str | None = Field(default=None, max_length=4000)
    # Kept temporarily for API compatibility; the authenticated principal is authoritative.
    actor: str | None = Field(default=None, min_length=1, max_length=255)


def missing() -> None:
    raise HTTPException(status_code=404, detail="Resource was not found.")


def _scope_endpoints(query, session: Session, principal: AuthPrincipal, field):
    allowed_rooms = permitted_room_ids(session, principal)
    if allowed_rooms is None:
        return query
    endpoint_ids = select(ManagedEndpointRecord.id).join(AssetRecord, AssetRecord.id == ManagedEndpointRecord.asset_id).where(AssetRecord.room_id.in_(allowed_rooms))
    return query.where(field.in_(endpoint_ids))


@router.get("/endpoints/{endpoint_id}/snapshots")
def snapshots(endpoint_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    scoped_endpoint(session, endpoint_id, principal)
    return [{
        "id": str(item.id), "captured_at": item.captured_at, "type": item.snapshot_type,
        "completeness": item.completeness, "normalizer_version": item.normalizer_version,
    } for item in session.scalars(select(HardwareSnapshotRecord).where(
        HardwareSnapshotRecord.managed_endpoint_id == endpoint_id,
    ).order_by(HardwareSnapshotRecord.captured_at.desc()))]


@router.get("/snapshots/{snapshot_id}")
def snapshot(snapshot_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    item = session.get(HardwareSnapshotRecord, snapshot_id)
    if not item:
        missing()
    scoped_endpoint(session, item.managed_endpoint_id, principal)
    components = list(session.scalars(select(ComponentObservationRecord).where(
        ComponentObservationRecord.hardware_snapshot_id == item.id,
    )))
    return {
        "id": str(item.id), "endpoint_id": str(item.managed_endpoint_id),
        "raw_inventory_id": str(item.raw_inventory_id), "captured_at": item.captured_at,
        "type": item.snapshot_type, "completeness": item.completeness,
        "normalizer_version": item.normalizer_version,
        "components": [{
            "id": str(component.id), "type": component.component_type,
            "serial": component.serial_number, "model": component.model,
            "manufacturer": component.manufacturer, "part_number": component.part_number,
            "capacity": component.capacity, "slot": component.slot,
            "confidence": component.confidence, "raw_data": component.raw_data,
        } for component in components],
    }


@router.get("/endpoints/{endpoint_id}/baseline")
def baseline(endpoint_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    scoped_endpoint(session, endpoint_id, principal)
    item = session.scalar(select(BaselineRecord).where(
        BaselineRecord.managed_endpoint_id == endpoint_id,
        BaselineRecord.status == "ACTIVE",
    ))
    return None if not item else {
        "id": str(item.id), "snapshot_id": str(item.hardware_snapshot_id),
        "accepted_at": item.accepted_at, "reason": item.reason,
    }


@router.post("/snapshots/{snapshot_id}/baseline", dependencies=[Depends(require_admin)])
def accept_baseline(snapshot_id: UUID, body: BaselineAccept, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    item = session.get(HardwareSnapshotRecord, snapshot_id)
    if not item:
        missing()
    accepted = accept_snapshot_as_baseline(session, item, body.reason)
    return {"id": str(accepted.id), "status": accepted.status, "snapshot_id": str(accepted.hardware_snapshot_id)}


@router.get("/changes")
def changes(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)], endpoint_id: UUID | None = None):
    query = select(ChangeEventRecord).order_by(ChangeEventRecord.detected_at.desc())
    if principal.organization_id:
        query = query.join(ManagedEndpointRecord).where(ManagedEndpointRecord.organization_id == principal.organization_id)
    query = _scope_endpoints(query, session, principal, ChangeEventRecord.managed_endpoint_id)
    if endpoint_id:
        scoped_endpoint(session, endpoint_id, principal)
        query = query.where(ChangeEventRecord.managed_endpoint_id == endpoint_id)
    return [{
        "id": str(item.id), "endpoint_id": str(item.managed_endpoint_id),
        "type": item.event_type, "component_type": item.component_type,
        "confidence": item.confidence, "severity": item.severity,
        "status": item.status, "evidence": item.evidence,
        "detected_at": item.detected_at,
    } for item in session.scalars(query)]


@router.get("/changes/{change_id}")
def change(change_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    item = session.get(ChangeEventRecord, change_id)
    if not item:
        missing()
    scoped_endpoint(session, item.managed_endpoint_id, principal)
    scoped_endpoint(session, item.managed_endpoint_id, principal)
    return {
        "id": str(item.id), "endpoint_id": str(item.managed_endpoint_id),
        "type": item.event_type, "component_type": item.component_type,
        "confidence": item.confidence, "severity": item.severity, "status": item.status,
        "evidence": item.evidence, "baseline_snapshot_id": str(item.baseline_snapshot_id),
        "current_snapshot_id": str(item.current_snapshot_id), "detected_at": item.detected_at,
    }


@router.get("/incidents")
def incidents(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)], endpoint_id: UUID | None = None):
    query = select(IncidentRecord).order_by(IncidentRecord.created_at.desc())
    if principal.organization_id:
        query = query.join(ManagedEndpointRecord).where(ManagedEndpointRecord.organization_id == principal.organization_id)
    query = _scope_endpoints(query, session, principal, IncidentRecord.managed_endpoint_id)
    if endpoint_id:
        scoped_endpoint(session, endpoint_id, principal)
        query = query.where(IncidentRecord.managed_endpoint_id == endpoint_id)
    return [{
        "id": str(item.id), "endpoint_id": str(item.managed_endpoint_id),
        "change_event_id": str(item.change_event_id), "status": item.status,
        "severity": item.severity, "title": item.title,
        "created_at": item.created_at, "resolved_at": item.resolved_at,
    } for item in session.scalars(query)]


@router.get("/incidents/{incident_id}")
def incident(incident_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    item = session.get(IncidentRecord, incident_id)
    if not item:
        missing()
    scoped_endpoint(session, item.managed_endpoint_id, principal)
    change_event = session.get(ChangeEventRecord, item.change_event_id)
    decisions = list(session.scalars(select(IncidentDecisionRecord).where(
        IncidentDecisionRecord.incident_id == item.id,
    ).order_by(IncidentDecisionRecord.created_at)))
    return {
        "id": str(item.id), "status": item.status, "severity": item.severity,
        "title": item.title, "description": item.description,
        "change_event_id": str(item.change_event_id), "resolved_at": item.resolved_at,
        "evidence": change_event.evidence if change_event else None,
        "decisions": [{
            "id": str(decision.id), "classification": decision.classification,
            "comment": decision.comment, "actor": decision.actor,
            "created_at": decision.created_at,
        } for decision in decisions],
    }


@router.post("/incidents/{incident_id}/decision")
def decision(
    incident_id: UUID, body: DecisionBody,
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_admin)],
):
    item = session.get(IncidentRecord, incident_id)
    if not item:
        missing()
    scoped_endpoint(session, item.managed_endpoint_id, principal)
    result = decide_incident(session, item, body.classification, principal.username, body.comment, False)
    return {"id": str(result.id), "incident_status": item.status}


@router.post("/incidents/{incident_id}/resolve")
def resolve(
    incident_id: UUID, body: DecisionBody,
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_admin)],
):
    item = session.get(IncidentRecord, incident_id)
    if not item:
        missing()
    scoped_endpoint(session, item.managed_endpoint_id, principal)
    result = decide_incident(session, item, body.classification, principal.username, body.comment, True)
    return {"id": str(result.id), "incident_status": item.status}


@router.get("/endpoints/{endpoint_id}/history")
def history(endpoint_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_viewer)]):
    scoped_endpoint(session, endpoint_id, principal)
    return [{
        "id": str(item.id), "type": item.event_type, "occurred_at": item.occurred_at,
        "entity_type": item.related_entity_type, "entity_id": str(item.related_entity_id),
        "message": item.message, "metadata": item.metadata_json,
    } for item in session.scalars(select(EndpointHistoryEntryRecord).where(
        EndpointHistoryEntryRecord.managed_endpoint_id == endpoint_id,
    ).order_by(EndpointHistoryEntryRecord.occurred_at.desc()))]
