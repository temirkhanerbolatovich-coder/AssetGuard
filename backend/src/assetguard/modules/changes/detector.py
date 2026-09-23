"""Evidence-aware comparison of the active baseline with the current snapshot."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.history.service import append_history
from assetguard.modules.snapshots.models import (
    ComponentObservationRecord,
    HardwareSnapshotRecord,
    ManagedEndpointRecord,
)

DETECTOR_VERSION = "0.2"


def detect_changes(session: Session, current: HardwareSnapshotRecord) -> list[ChangeEventRecord]:
    baseline = session.scalar(select(BaselineRecord).where(
        BaselineRecord.managed_endpoint_id == current.managed_endpoint_id,
        BaselineRecord.status == "ACTIVE",
    ))
    if not baseline or baseline.hardware_snapshot_id == current.id:
        return []
    base = session.get(HardwareSnapshotRecord, baseline.hardware_snapshot_id)
    if base is None:
        return []
    created: list[ChangeEventRecord] = []
    hostname_change = getattr(current, "_hostname_change", None)
    if hostname_change:
        previous, present = hostname_change
        event = _create_event(
            session, baseline, base, current, "ENDPOINT", "HOSTNAME_CHANGED",
            None, None, "HIGH",
            {"previous": {"hostname": previous}, "current": {"hostname": present}, "matching": "stable endpoint identifiers"},
            stable_suffix=f"{previous.casefold()}|{present.casefold()}",
        )
        if event:
            created.append(event)

    for component_type in ("RAM", "STORAGE"):
        if current.completeness.get(component_type) != "COMPLETE":
            continue
        old = list(session.scalars(select(ComponentObservationRecord).where(
            ComponentObservationRecord.hardware_snapshot_id == base.id,
            ComponentObservationRecord.component_type == component_type,
        )))
        new = list(session.scalars(select(ComponentObservationRecord).where(
            ComponentObservationRecord.hardware_snapshot_id == current.id,
            ComponentObservationRecord.component_type == component_type,
        )))
        created.extend(_compare_category(session, baseline, base, current, component_type, old, new))

    endpoint = session.get(ManagedEndpointRecord, current.managed_endpoint_id)
    if endpoint:
        for event in created:
            append_history(
                session, endpoint=endpoint, event_type="HARDWARE_CHANGE_DETECTED" if event.component_type != "ENDPOINT" else event.event_type,
                related_entity_type="ChangeEvent", related_entity_id=event.id,
                message=f"{event.component_type}: {event.event_type} detected.",
                metadata={"confidence": event.confidence, "severity": event.severity},
            )
    session.commit()
    return created


def _compare_category(session, baseline, base, current, component_type, old, new):
    created: list[ChangeEventRecord] = []
    old_by_key = {_key(item): item for item in old}
    new_by_key = {_key(item): item for item in new}
    matched = old_by_key.keys() & new_by_key.keys()
    for key in matched:
        previous, present = old_by_key[key], new_by_key[key]
        if _material(previous) != _material(present):
            event = _component_event(session, baseline, base, current, component_type, "COMPONENT_CHANGED", previous, present)
            if event:
                created.append(event)

    unmatched_old = [item for key, item in old_by_key.items() if key not in matched]
    unmatched_new = [item for key, item in new_by_key.items() if key not in matched]
    replacements: list[tuple[ComponentObservationRecord, ComponentObservationRecord]] = []
    for previous in list(unmatched_old):
        present = next((item for item in unmatched_new if previous.slot and item.slot == previous.slot), None)
        if present:
            replacements.append((previous, present))
            unmatched_old.remove(previous)
            unmatched_new.remove(present)
    if len(unmatched_old) == len(unmatched_new) == 1 and _replacement_is_supported(unmatched_old[0], unmatched_new[0]):
        replacements.append((unmatched_old.pop(), unmatched_new.pop()))
    for previous, present in replacements:
        event = _component_event(session, baseline, base, current, component_type, "COMPONENT_REPLACED", previous, present)
        if event:
            created.append(event)
    for previous in unmatched_old:
        event = _component_event(session, baseline, base, current, component_type, "COMPONENT_REMOVED", previous, None)
        if event:
            created.append(event)
    for present in unmatched_new:
        event = _component_event(session, baseline, base, current, component_type, "COMPONENT_ADDED", None, present)
        if event:
            created.append(event)
    return created


def _key(observation: ComponentObservationRecord) -> str:
    return str(observation.component_identity_id or observation.source_key or observation.id)


def _material(observation: ComponentObservationRecord) -> tuple:
    return observation.manufacturer, observation.model, observation.capacity, observation.slot, observation.part_number


def _replacement_is_supported(previous: ComponentObservationRecord, present: ComponentObservationRecord) -> bool:
    return previous.confidence == "HIGH" and present.confidence == "HIGH" and previous.component_type == present.component_type


def _component_event(session, baseline, base, current, component_type, event_type, previous, present):
    observation = previous or present
    confidence = min((item.confidence for item in (previous, present) if item), key=lambda value: {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}[value])
    evidence = {
        "baseline_snapshot_id": str(base.id),
        "current_snapshot_id": str(current.id),
        "previous": previous.raw_data if previous else None,
        "current": present.raw_data if present else None,
        "matching": "identity, serial, source fingerprint, then slot-aware replacement",
    }
    stable_values = {
        "previous": previous.raw_data if previous else None,
        "current": present.raw_data if present else None,
    }
    suffix = hashlib.sha256(json.dumps(stable_values, sort_keys=True, default=str).encode()).hexdigest()
    return _create_event(
        session, baseline, base, current, component_type, event_type,
        previous, present, confidence, evidence, suffix,
    )


def _create_event(
    session, baseline, base, current, component_type, event_type,
    previous, present, confidence, evidence, stable_suffix,
):
    stable = f"{baseline.id}|{component_type}|{event_type}|{_key(previous) if previous else ''}|{_key(present) if present else ''}|{stable_suffix}"
    dedup_key = hashlib.sha256(stable.encode()).hexdigest()
    if session.scalar(select(ChangeEventRecord).where(ChangeEventRecord.dedup_key == dedup_key)):
        return None
    event = ChangeEventRecord(
        managed_endpoint_id=current.managed_endpoint_id,
        baseline_id=baseline.id,
        baseline_snapshot_id=base.id,
        current_snapshot_id=current.id,
        component_type=component_type,
        previous_observation_id=previous.id if previous else None,
        current_observation_id=present.id if present else None,
        event_type=event_type,
        confidence=confidence,
        severity="HIGH" if confidence == "HIGH" else "MEDIUM",
        status="OPEN",
        evidence=evidence,
        detected_at=datetime.now(UTC),
        detector_version=DETECTOR_VERSION,
        dedup_key=dedup_key,
    )
    session.add(event)
    session.flush()
    return event
