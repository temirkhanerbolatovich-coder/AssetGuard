from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.admin_assets import require_viewer
from assetguard.modules.inventory.models import RawInventoryRecord

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_viewer)])


def _summary(item: RawInventoryRecord) -> dict:
    return {
        "id": str(item.id),
        "endpoint_id": str(item.managed_endpoint_id) if item.managed_endpoint_id else None,
        "source": item.source,
        "source_version": item.source_version,
        "schema_version": item.schema_version,
        "received_at": item.received_at,
        "payload_hash": item.payload_hash,
        "inventory_type": item.inventory_type,
        "processing_status": item.processing_status,
        "processing_error": item.processing_error,
        "idempotency_key": item.ingest_idempotency_key,
    }


@router.get("/inventories")
def list_inventories(
    session: Annotated[Session, Depends(get_session)],
    endpoint_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    query = select(RawInventoryRecord).order_by(RawInventoryRecord.received_at.desc()).limit(limit)
    if endpoint_id:
        query = query.where(RawInventoryRecord.managed_endpoint_id == endpoint_id)
    return [_summary(item) for item in session.scalars(query)]


@router.get("/inventories/{inventory_id}")
def inventory_detail(inventory_id: UUID, session: Annotated[Session, Depends(get_session)]):
    item = session.get(RawInventoryRecord, inventory_id)
    if not item:
        raise HTTPException(404, "Raw inventory was not found.")
    return {**_summary(item), "payload": item.payload}
