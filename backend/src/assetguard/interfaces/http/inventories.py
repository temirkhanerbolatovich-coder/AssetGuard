"""Protected internal boundary for inventory source adapters."""

from __future__ import annotations

import json
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session
from assetguard.modules.inventory.service import (
    IdempotencyConflictError,
    RawInventoryIngestCommand,
    ingest_raw_inventory,
)
from assetguard.modules.snapshots.normalizer import normalize_raw_inventory
from assetguard.modules.changes.detector import detect_changes
from assetguard.modules.incidents.service import create_incidents_for_events


router = APIRouter(prefix="/internal/inventories", tags=["inventory"])


def require_ingest_secret(
    supplied_secret: Annotated[
        str | None, Header(alias="X-AssetGuard-Ingest-Token")
    ] = None,
) -> None:
    """Reject unauthenticated inventory sources without leaking the expected token."""
    if not supplied_secret or not secrets.compare_digest(
        supplied_secret, get_settings().inventory_shared_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid inventory source credentials.",
        )


@router.post("", dependencies=[Depends(require_ingest_secret)])
async def receive_inventory(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    idempotency_key: Annotated[
        str, Header(alias="X-AssetGuard-Idempotency-Key", min_length=1, max_length=128)
    ],
    source: Annotated[
        str, Header(alias="X-AssetGuard-Source", min_length=1, max_length=64)
    ],
    source_version: Annotated[
        str | None, Header(alias="X-AssetGuard-Source-Version", max_length=64)
    ] = None,
    schema_version: Annotated[
        str | None, Header(alias="X-AssetGuard-Schema-Version", max_length=64)
    ] = None,
    inventory_type: Annotated[
        str, Header(alias="X-AssetGuard-Inventory-Type", pattern="^(FULL|PARTIAL|UNKNOWN)$")
    ] = "UNKNOWN",
) -> JSONResponse:
    """Store a source payload exactly once before any normalization occurs."""
    configured_limit = get_settings().max_inventory_payload_bytes
    declared_size = request.headers.get("content-length")
    if declared_size and declared_size.isdecimal() and int(declared_size) > configured_limit:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    body = await request.body()
    if len(body) > configured_limit:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory body must contain valid JSON.",
        ) from error
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Inventory root must be a JSON object.",
        )

    try:
        result = ingest_raw_inventory(
            session,
            RawInventoryIngestCommand(
                source=source,
                source_version=source_version,
                schema_version=schema_version,
                inventory_type=inventory_type,
                idempotency_key=idempotency_key,
                payload=payload,
            ),
        )
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    raw_inventory = result.raw_inventory
    if not result.duplicate:
        try:
            snapshot = normalize_raw_inventory(session, raw_inventory)
            events = detect_changes(session, snapshot)
            create_incidents_for_events(session, events)
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return JSONResponse(
        status_code=(status.HTTP_200_OK if result.duplicate else status.HTTP_202_ACCEPTED),
        content={
            "raw_inventory_id": str(raw_inventory.id),
            "duplicate": result.duplicate,
            "processing_status": raw_inventory.processing_status,
            "snapshot_id": str(snapshot.id) if not result.duplicate else None,
        },
    )
