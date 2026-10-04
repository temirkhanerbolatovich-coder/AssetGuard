from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.history.service import append_history
from assetguard.modules.incidents.models import IncidentDecisionRecord, IncidentRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord
from assetguard.modules.assets.models import AssetRecord
from assetguard.modules.notifications.service import enqueue_notification


def create_incidents_for_events(session: Session, events: list[ChangeEventRecord]) -> list[IncidentRecord]:
    created = []
    for event in events:
        if session.scalar(select(IncidentRecord).where(IncidentRecord.change_event_id == event.id)):
            continue
        incident = IncidentRecord(
            managed_endpoint_id=event.managed_endpoint_id, change_event_id=event.id,
            status="OPEN", severity=event.severity,
            title=f"{event.component_type}: {event.event_type}",
            description="Automatically created from an explainable inventory change.",
            created_at=datetime.now(UTC), resolved_at=None,
        )
        session.add(incident)
        session.flush()
        endpoint = session.get(ManagedEndpointRecord, incident.managed_endpoint_id)
        if endpoint:
            asset = session.get(AssetRecord, endpoint.asset_id) if endpoint.asset_id else None
            components = {"RAM": "Оперативная память", "STORAGE": "Накопитель", "ENDPOINT": "Идентификаторы компьютера"}
            changes = {"COMPONENT_CHANGED": "изменились характеристики", "COMPONENT_REPLACED": "изменился состав компонента",
                       "COMPONENT_REMOVED": "компонент не обнаружен", "COMPONENT_ADDED": "обнаружен новый компонент",
                       "HOSTNAME_CHANGED": "изменилось имя компьютера", "DEVICE_IDENTITY_CHANGED": "изменились идентификаторы"}
            enqueue_notification(
                session, event_key=f"technical:{incident.id}:opened",
                organization_id=endpoint.organization_id or (asset.organization_id if asset else None),
                room_id=asset.room_id if asset else None,
                title="Новое техническое расхождение", subject=endpoint.hostname or str(endpoint.id),
                context=f"{components.get(event.component_type, event.component_type)}: {changes.get(event.event_type, event.event_type)}. Сравнение «Было → Стало» доступно в карточке; проверьте evidence и примите решение.",
                route=f"#incident={incident.id}", severity=incident.severity, occurred_at=incident.created_at,
            )
            append_history(
                session, endpoint=endpoint, event_type="INCIDENT_CREATED",
                related_entity_type="Incident", related_entity_id=incident.id,
                message="Incident created from ChangeEvent.",
                metadata={"change_event_id": str(event.id)},
            )
        created.append(incident)
    session.commit()
    return created


def decide_incident(
    session: Session, incident: IncidentRecord, classification: str, actor: str,
    comment: str | None = None, resolve: bool = False,
) -> IncidentDecisionRecord:
    decision = IncidentDecisionRecord(
        incident_id=incident.id, classification=classification,
        comment=comment, actor=actor, created_at=datetime.now(UTC),
    )
    session.add(decision)
    incident.status = "RESOLVED" if resolve else "UNDER_REVIEW"
    incident.resolved_at = datetime.now(UTC) if resolve else None
    change = session.get(ChangeEventRecord, incident.change_event_id)
    if resolve and change:
        change.status = "DISMISSED" if classification == "FALSE_POSITIVE" else "RESOLVED"
    session.flush()
    endpoint = session.get(ManagedEndpointRecord, incident.managed_endpoint_id)
    if endpoint:
        append_history(
            session, endpoint=endpoint,
            event_type="INCIDENT_RESOLVED" if resolve else "INCIDENT_CLASSIFIED",
            related_entity_type="Incident", related_entity_id=incident.id,
            message=f"Incident classified as {classification}.",
            metadata={"classification": classification, "actor": actor, "decision_id": str(decision.id), "comment": comment},
        )
    session.commit()
    session.refresh(decision)
    return decision
