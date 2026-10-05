"""Non-sensitive operational health endpoints."""

import shutil
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import case, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.infrastructure.config import get_settings
from assetguard.interfaces.http.authorization import require_admin, require_viewer
from assetguard.modules.assets.models import AssetRecord
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.identity.location_access import permitted_room_ids
from assetguard.modules.inventory.models import RawInventoryRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord
from assetguard.modules.notifications.models import TelegramNotificationRecord


router = APIRouter(tags=["operations"])


def _existing_storage_path(storage_root: Path) -> Path:
    """Find an existing ancestor without creating state during a health read."""
    candidate = storage_root
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


@router.get("/health")
async def health() -> dict[str, str]:
    """Report that the API process is reachable without exposing dependencies."""
    return {
        "status": "ok",
        "service": "assetguard",
        "version": "0.1.0",
    }


@router.get("/health/ready")
def readiness(session: Annotated[Session, Depends(get_session)]):
    """Return 503 when the API cannot reach its mandatory PostgreSQL database."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Do not expose database topology or driver messages to an unauthenticated probe.
        return JSONResponse(status_code=503, content={"status": "not_ready", "service": "assetguard"})
    return {"status": "ready", "service": "assetguard"}


@router.get("/admin/operations/status")
def operations_status(
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_viewer)],
):
    """Provide a compact, tenant-safe operational snapshot for the dashboard."""
    threshold = datetime.now(UTC) - timedelta(hours=get_settings().endpoint_stale_after_hours)
    effective_status = case(
        (ManagedEndpointRecord.status == "IDENTITY_CONFLICT", "IDENTITY_CONFLICT"),
        (ManagedEndpointRecord.status == "OFFLINE", "OFFLINE"),
        (ManagedEndpointRecord.last_seen_at < threshold, "STALE"),
        else_=ManagedEndpointRecord.status,
    )
    endpoint_query = select(effective_status, func.count(ManagedEndpointRecord.id)).group_by(effective_status)
    failed_query = select(
        func.count(RawInventoryRecord.id), func.max(RawInventoryRecord.received_at),
    ).where(RawInventoryRecord.processing_status == "FAILED")
    latest_inventory_query = select(func.max(RawInventoryRecord.received_at))
    notification_query = select(
        func.count(case((TelegramNotificationRecord.status == "PENDING", 1))),
        func.count(case(((TelegramNotificationRecord.status == "PENDING") & (TelegramNotificationRecord.attempts > 0), 1))),
    )
    if principal.organization_id:
        endpoint_query = endpoint_query.where(ManagedEndpointRecord.organization_id == principal.organization_id)
        failed_query = failed_query.join(ManagedEndpointRecord, ManagedEndpointRecord.id == RawInventoryRecord.managed_endpoint_id).where(ManagedEndpointRecord.organization_id == principal.organization_id)
        latest_inventory_query = latest_inventory_query.join(ManagedEndpointRecord, ManagedEndpointRecord.id == RawInventoryRecord.managed_endpoint_id).where(ManagedEndpointRecord.organization_id == principal.organization_id)
        notification_query = notification_query.where(TelegramNotificationRecord.organization_id == principal.organization_id)
    allowed_rooms = permitted_room_ids(session, principal)
    if allowed_rooms is not None:
        endpoint_ids = select(ManagedEndpointRecord.id).join(
            AssetRecord, AssetRecord.id == ManagedEndpointRecord.asset_id,
        ).where(AssetRecord.room_id.in_(allowed_rooms))
        endpoint_query = endpoint_query.where(ManagedEndpointRecord.id.in_(endpoint_ids))
        failed_query = failed_query.where(RawInventoryRecord.managed_endpoint_id.in_(endpoint_ids))
        latest_inventory_query = latest_inventory_query.where(RawInventoryRecord.managed_endpoint_id.in_(endpoint_ids))
        notification_query = notification_query.where(TelegramNotificationRecord.room_id.in_(allowed_rooms))

    endpoint_counts = {status: count for status, count in session.execute(endpoint_query)}
    failed_count, last_failed_at = session.execute(failed_query).one()
    latest_inventory_at = session.scalar(latest_inventory_query)
    pending_notifications, retrying_notifications = session.execute(notification_query).one()

    database_bytes = None
    try:
        database_bytes = session.scalar(text("SELECT pg_database_size(current_database())"))
    except SQLAlchemyError:
        # A restricted production DB role may legitimately lack this privilege.
        session.rollback()

    storage_root = get_settings().vision_storage_root
    usage = shutil.disk_usage(_existing_storage_path(storage_root))
    return {
        "database": {"status": "ready", "bytes": database_bytes},
        "storage": {"free_bytes": usage.free, "total_bytes": usage.total},
        "agents": {
            "total": sum(endpoint_counts.values()),
            "online": endpoint_counts.get("ONLINE", 0),
            "offline": endpoint_counts.get("OFFLINE", 0),
            "stale": endpoint_counts.get("STALE", 0),
            "identity_conflicts": endpoint_counts.get("IDENTITY_CONFLICT", 0),
            "last_inventory_at": latest_inventory_at,
            "stale_after_hours": get_settings().endpoint_stale_after_hours,
        },
        "ingest": {"failed": failed_count, "last_failed_at": last_failed_at},
        "notifications": {"pending": pending_notifications, "retrying": retrying_notifications},
    }


def _notification_view(item: TelegramNotificationRecord) -> dict:
    """Expose delivery metadata only; never return recipient, body or transport secrets."""
    route = item.payload.get("route") if isinstance(item.payload, dict) else None
    safe_route = None
    if isinstance(route, str) and "=" in route:
        prefix, identifier = route.split("=", 1)
        if prefix in {"#incident", "#physical-incident", "#room"}:
            try:
                safe_route = f"{prefix}={UUID(identifier)}"
            except ValueError:
                pass
    error = item.last_error_code
    known_errors = {"NETWORK_ERROR", "INVALID_RESPONSE", "NOT_ACCEPTED", "NO_MESSAGE_ID", "WRONG_DESTINATION", "INVALID_PAYLOAD", "INVALID_ROUTE"}
    if error and error not in known_errors and not re.fullmatch(r"HTTP_\d{3}", error):
        error = "UNKNOWN_ERROR"
    return {
        "id": str(item.id),
        "status": "RETRYING" if item.status == "PENDING" and item.attempts else item.status,
        "attempts": item.attempts, "created_at": item.created_at,
        "next_attempt_at": item.next_attempt_at if item.status == "PENDING" else None,
        "sent_at": item.sent_at, "last_error_code": error, "route": safe_route,
    }


@router.get("/admin/notifications")
def notifications(
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_admin)],
    status: Literal["PENDING", "RETRYING", "SENT"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
):
    """Read a tenant-scoped queue page. SENT confirms Telegram acceptance, not reading."""
    query = select(TelegramNotificationRecord)
    if principal.organization_id:
        query = query.where(TelegramNotificationRecord.organization_id == principal.organization_id)
    pending = (TelegramNotificationRecord.status == "PENDING") & (TelegramNotificationRecord.attempts == 0)
    retrying = (TelegramNotificationRecord.status == "PENDING") & (TelegramNotificationRecord.attempts > 0)
    sent = TelegramNotificationRecord.status == "SENT"
    scoped = query.subquery()
    summary_row = session.execute(select(
        func.count(case(((scoped.c.status == "PENDING") & (scoped.c.attempts == 0), 1))),
        func.count(case(((scoped.c.status == "PENDING") & (scoped.c.attempts > 0), 1))),
        func.count(case((scoped.c.status == "SENT", 1))),
    )).one()
    if status:
        query = query.where({"PENDING": pending, "RETRYING": retrying, "SENT": sent}[status])
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.scalars(query.order_by(TelegramNotificationRecord.created_at.desc(), TelegramNotificationRecord.id.desc()).offset(offset).limit(limit))
    return {"summary": dict(zip(("pending", "retrying", "sent"), summary_row)),
            "total": total, "limit": limit, "offset": offset,
            "items": [_notification_view(item) for item in rows]}
