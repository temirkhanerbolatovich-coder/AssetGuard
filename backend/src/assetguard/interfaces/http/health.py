"""Non-sensitive operational health endpoints."""

import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.infrastructure.config import get_settings
from assetguard.interfaces.http.admin_assets import require_viewer
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.inventory.models import RawInventoryRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord


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
    endpoint_query = select(ManagedEndpointRecord.status, func.count(ManagedEndpointRecord.id)).group_by(ManagedEndpointRecord.status)
    failed_query = select(
        func.count(RawInventoryRecord.id), func.max(RawInventoryRecord.received_at),
    ).where(RawInventoryRecord.processing_status == "FAILED")
    latest_inventory_query = select(func.max(RawInventoryRecord.received_at))
    if principal.organization_id:
        endpoint_query = endpoint_query.where(ManagedEndpointRecord.organization_id == principal.organization_id)
        failed_query = failed_query.join(ManagedEndpointRecord, ManagedEndpointRecord.id == RawInventoryRecord.managed_endpoint_id).where(ManagedEndpointRecord.organization_id == principal.organization_id)
        latest_inventory_query = latest_inventory_query.join(ManagedEndpointRecord, ManagedEndpointRecord.id == RawInventoryRecord.managed_endpoint_id).where(ManagedEndpointRecord.organization_id == principal.organization_id)

    endpoint_counts = {status: count for status, count in session.execute(endpoint_query)}
    failed_count, last_failed_at = session.execute(failed_query).one()
    latest_inventory_at = session.scalar(latest_inventory_query)

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
        },
        "ingest": {"failed": failed_count, "last_failed_at": last_failed_at},
    }
