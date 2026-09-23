from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.modules.history.service import append_history
from assetguard.modules.snapshots.models import ManagedEndpointRecord


def evaluate_last_seen(session: Session, stale_after_hours: int) -> int:
    threshold = datetime.now(UTC) - timedelta(hours=stale_after_hours)
    changed = 0
    for endpoint in session.scalars(select(ManagedEndpointRecord).where(
        ManagedEndpointRecord.last_seen_at < threshold,
        ManagedEndpointRecord.status != "REQUIRES_VERIFICATION",
    )):
        endpoint.status = "REQUIRES_VERIFICATION"
        endpoint.updated_at = datetime.now(UTC)
        append_history(
            session, endpoint=endpoint, event_type="ENDPOINT_REQUIRES_VERIFICATION",
            related_entity_type="ManagedEndpoint", related_entity_id=endpoint.id,
            message="Endpoint exceeded the configured last-seen threshold; operator verification is required.",
            metadata={"last_seen_at": endpoint.last_seen_at.isoformat(), "threshold_hours": stale_after_hours},
        )
        changed += 1
    session.commit()
    return changed
