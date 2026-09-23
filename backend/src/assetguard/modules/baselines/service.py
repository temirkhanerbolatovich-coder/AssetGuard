from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.modules.baselines.models import BaselineRecord
from assetguard.modules.history.service import append_history
from assetguard.modules.snapshots.models import HardwareSnapshotRecord, ManagedEndpointRecord


def accept_snapshot_as_baseline(
    session: Session, snapshot: HardwareSnapshotRecord, reason: str | None = None,
) -> BaselineRecord:
    existing = session.scalar(select(BaselineRecord).where(BaselineRecord.hardware_snapshot_id == snapshot.id))
    if existing and existing.status == "ACTIVE":
        return existing
    active = session.scalar(select(BaselineRecord).where(
        BaselineRecord.managed_endpoint_id == snapshot.managed_endpoint_id,
        BaselineRecord.status == "ACTIVE",
    ))
    now = datetime.now(UTC)
    if active:
        active.status = "SUPERSEDED"
        active.superseded_at = now
    baseline = existing or BaselineRecord(
        managed_endpoint_id=snapshot.managed_endpoint_id,
        hardware_snapshot_id=snapshot.id,
        status="ACTIVE", accepted_at=now, superseded_at=None, reason=reason,
    )
    if existing:
        existing.status = "ACTIVE"
        existing.accepted_at = now
        existing.superseded_at = None
        existing.reason = reason
    else:
        session.add(baseline)
    session.flush()
    endpoint = session.get(ManagedEndpointRecord, snapshot.managed_endpoint_id)
    if endpoint:
        append_history(
            session, endpoint=endpoint, event_type="BASELINE_ACCEPTED",
            related_entity_type="Baseline", related_entity_id=baseline.id,
            message="Snapshot explicitly accepted as baseline.",
            metadata={"snapshot_id": str(snapshot.id), "reason": reason}, occurred_at=now,
        )
    session.commit()
    session.refresh(baseline)
    return baseline
