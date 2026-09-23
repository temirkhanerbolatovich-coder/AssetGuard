from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.incidents.models import EndpointHistoryEntryRecord, IncidentDecisionRecord, IncidentRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord  # registers FK target metadata

def create_incidents_for_events(session: Session, events: list[ChangeEventRecord]) -> list[IncidentRecord]:
    created=[]
    for event in events:
        if session.scalar(select(IncidentRecord).where(IncidentRecord.change_event_id == event.id)): continue
        incident=IncidentRecord(managed_endpoint_id=event.managed_endpoint_id, change_event_id=event.id, status="OPEN", severity=event.severity, title=f"{event.component_type}: {event.event_type}", description="Automatically created from an explainable hardware change.", created_at=datetime.now(UTC), resolved_at=None)
        session.add(incident); session.flush(); _history(session, incident, "INCIDENT_CREATED", "Incident created from ChangeEvent."); created.append(incident)
    session.commit(); return created

def decide_incident(session: Session, incident: IncidentRecord, classification: str, actor: str, comment: str | None = None, resolve: bool = False) -> IncidentDecisionRecord:
    decision=IncidentDecisionRecord(incident_id=incident.id, classification=classification, comment=comment, actor=actor, created_at=datetime.now(UTC)); session.add(decision)
    incident.status="RESOLVED" if resolve else "UNDER_REVIEW"; incident.resolved_at=datetime.now(UTC) if resolve else None
    _history(session, incident, "INCIDENT_RESOLVED" if resolve else "INCIDENT_CLASSIFIED", f"Incident classified as {classification}.", {"classification":classification,"actor":actor,"decision_id":str(decision.id)})
    session.commit(); session.refresh(decision); return decision

def _history(session, incident, event_type, message, metadata=None):
    session.add(EndpointHistoryEntryRecord(managed_endpoint_id=incident.managed_endpoint_id,event_type=event_type,occurred_at=datetime.now(UTC),related_entity_type="Incident",related_entity_id=incident.id,message=message,metadata_json=metadata or {}))
