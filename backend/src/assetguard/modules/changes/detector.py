import hashlib
import json
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.changes.models import ChangeEventRecord
from assetguard.modules.snapshots.models import ComponentObservationRecord, HardwareSnapshotRecord

DETECTOR_VERSION = "0.1"

def detect_changes(session: Session, current: HardwareSnapshotRecord) -> list[ChangeEventRecord]:
    baseline = session.scalar(select(BaselineRecord).where(BaselineRecord.managed_endpoint_id == current.managed_endpoint_id, BaselineRecord.status == "ACTIVE"))
    if not baseline or baseline.hardware_snapshot_id == current.id: return []
    base = session.get(HardwareSnapshotRecord, baseline.hardware_snapshot_id)
    created: list[ChangeEventRecord] = []
    for component_type in ("RAM", "STORAGE"):
        if current.completeness.get(component_type) != "COMPLETE": continue
        old = list(session.scalars(select(ComponentObservationRecord).where(ComponentObservationRecord.hardware_snapshot_id == base.id, ComponentObservationRecord.component_type == component_type)))
        new = list(session.scalars(select(ComponentObservationRecord).where(ComponentObservationRecord.hardware_snapshot_id == current.id, ComponentObservationRecord.component_type == component_type)))
        old_by_key = {_key(o): o for o in old}; new_by_key = {_key(o): o for o in new}
        for key, observation in old_by_key.items():
            if key not in new_by_key: created.extend(_event(session, baseline, base, current, component_type, "COMPONENT_REMOVED", observation, None))
        for key, observation in new_by_key.items():
            if key not in old_by_key: created.extend(_event(session, baseline, base, current, component_type, "COMPONENT_ADDED", None, observation))
    session.commit(); return created

def _key(observation: ComponentObservationRecord) -> str:
    return str(observation.component_identity_id or observation.source_key or observation.id)

def _event(session, baseline, base, current, component_type, event_type, previous, present):
    stable = f"{baseline.id}|{component_type}|{event_type}|{_key(previous) if previous else ''}|{_key(present) if present else ''}"
    dedup_key = hashlib.sha256(stable.encode()).hexdigest()
    existing = session.scalar(select(ChangeEventRecord).where(ChangeEventRecord.dedup_key == dedup_key))
    if existing: return []
    observation = previous or present
    evidence = {"baseline_snapshot_id": str(base.id), "current_snapshot_id": str(current.id), "previous": previous.raw_data if previous else None, "current": present.raw_data if present else None, "matching": "component identity or source fingerprint"}
    event = ChangeEventRecord(managed_endpoint_id=current.managed_endpoint_id, baseline_id=baseline.id, baseline_snapshot_id=base.id, current_snapshot_id=current.id, component_type=component_type, previous_observation_id=previous.id if previous else None, current_observation_id=present.id if present else None, event_type=event_type, confidence=observation.confidence, severity="HIGH" if observation.confidence == "HIGH" else "MEDIUM", status="OPEN", evidence=evidence, detected_at=datetime.now(UTC), detector_version=DETECTOR_VERSION, dedup_key=dedup_key)
    session.add(event); session.flush(); return [event]
