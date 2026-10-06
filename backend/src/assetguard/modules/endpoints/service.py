from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.config import get_settings
from assetguard.modules.history.service import append_history
from assetguard.modules.snapshots.models import ManagedEndpointRecord


def endpoint_connection_status(endpoint: ManagedEndpointRecord, *, now: datetime | None = None) -> str:
    """Compute report freshness without changing the stored status or history."""
    if endpoint.status in {"IDENTITY_CONFLICT", "OFFLINE"}:
        return endpoint.status
    threshold = (now or datetime.now(UTC)) - timedelta(hours=get_settings().endpoint_stale_after_hours)
    return "STALE" if endpoint.last_seen_at < threshold else endpoint.status


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
