from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.snapshots.models import HardwareSnapshotRecord
from assetguard.modules.incidents.models import EndpointHistoryEntryRecord

def accept_snapshot_as_baseline(session: Session, snapshot: HardwareSnapshotRecord, reason: str | None = None) -> BaselineRecord:
    existing = session.scalar(select(BaselineRecord).where(BaselineRecord.hardware_snapshot_id == snapshot.id))
    if existing and existing.status == "ACTIVE": return existing
    active = session.scalar(select(BaselineRecord).where(BaselineRecord.managed_endpoint_id == snapshot.managed_endpoint_id, BaselineRecord.status == "ACTIVE"))
    now = datetime.now(UTC)
    if active:
        active.status, active.superseded_at = "SUPERSEDED", now
    baseline = existing or BaselineRecord(managed_endpoint_id=snapshot.managed_endpoint_id, hardware_snapshot_id=snapshot.id, status="ACTIVE", accepted_at=now, superseded_at=None, reason=reason)
    if existing:
        existing.status, existing.accepted_at, existing.superseded_at, existing.reason = "ACTIVE", now, None, reason
    else: session.add(baseline)
    session.flush()
    session.add(EndpointHistoryEntryRecord(managed_endpoint_id=snapshot.managed_endpoint_id,event_type="BASELINE_ACCEPTED",occurred_at=now,related_entity_type="Baseline",related_entity_id=baseline.id,message="Snapshot explicitly accepted as baseline.",metadata_json={"snapshot_id":str(snapshot.id),"reason":reason}))
    session.commit(); session.refresh(baseline); return baseline
