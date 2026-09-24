"""Observed native GLPI Agent 1.19 XML transport boundary."""

from __future__ import annotations

import base64
import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session
from assetguard.modules.changes.detector import detect_changes
from assetguard.modules.incidents.service import create_incidents_for_events
from assetguard.modules.inventory.adapters import (
    DirectGlpiAgentAdapter,
    InventorySourceMetadata,
)
from assetguard.modules.inventory.service import ingest_raw_inventory
from assetguard.modules.snapshots.models import ManagedEndpointRecord
from assetguard.modules.identity.auth import verify_password
from assetguard.modules.identity.models import AgentCredentialRecord
from assetguard.modules.snapshots.normalizer import normalize_raw_inventory

router = APIRouter(prefix="/glpi-agent", tags=["inventory"])
REPLY = b"<?xml version='1.0' encoding='UTF-8'?><REPLY><RESPONSE>SEND</RESPONSE><PROLOG_FREQ>24</PROLOG_FREQ></REPLY>\n"
AUTH_CHALLENGE = {"WWW-Authenticate": 'Basic realm="AssetGuard"'}


def require_glpi_basic_auth(
    session: Annotated[Session, Depends(get_session)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AgentCredentialRecord | None:
    if not authorization or not authorization.startswith("Basic "):
        raise HTTPException(401, "GLPI Agent credentials are required.", headers=AUTH_CHALLENGE)
    try:
        username, password = base64.b64decode(authorization[6:], validate=True).decode("utf-8").split(":", 1)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(401, "Invalid GLPI Agent credentials.", headers=AUTH_CHALLENGE)
    credential = session.scalar(select(AgentCredentialRecord).where(AgentCredentialRecord.username == username))
    if credential and credential.status == "ACTIVE" and verify_password(password, credential.secret_hash):
        return credential
    settings = get_settings()
    valid = [settings.inventory_shared_secret, settings.previous_inventory_shared_secret]
    if username != "assetguard" or not any(candidate and secrets.compare_digest(password, candidate) for candidate in valid):
        raise HTTPException(401, "Invalid GLPI Agent credentials.", headers=AUTH_CHALLENGE)
    return None


@router.post("")
async def receive_glpi_agent(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    credential: Annotated[AgentCredentialRecord | None, Depends(require_glpi_basic_auth)],
) -> Response:
    limit = get_settings().max_inventory_payload_bytes
    declared = request.headers.get("content-length")
    if declared and declared.isdecimal() and int(declared) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    raw_xml = await request.body()
    if len(raw_xml) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    if request.headers.get("content-encoding"):
        raise HTTPException(415, "Configure GLPI Agent with no-compression for this endpoint.")
    try:
        observed = DirectGlpiAgentAdapter().parse(raw_xml)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    if observed.query == "PROLOG":
        return Response(REPLY, media_type="application/xml")

    metadata = InventorySourceMetadata(
        source="GLPI_AGENT", source_version=observed.source_version,
        schema_version="glpi-agent-legacy-xml-v1", inventory_type=observed.inventory_type,
        idempotency_key=observed.idempotency_key,
    )
    result = DirectGlpiAgentAdapter().to_ingest_command(observed.payload or {}, metadata)
    ingested = ingest_raw_inventory(session, result)
    if ingested.duplicate:
        if ingested.raw_inventory.managed_endpoint_id:
            endpoint = session.get(ManagedEndpointRecord, ingested.raw_inventory.managed_endpoint_id)
            if endpoint:
                endpoint.last_seen_at = datetime.now(UTC)
                endpoint.status = "ONLINE"
                endpoint.updated_at = datetime.now(UTC)
                session.commit()
    else:
        try:
            snapshot = normalize_raw_inventory(session, ingested.raw_inventory)
            if credential and credential.managed_endpoint_id is None:
                credential.managed_endpoint_id = snapshot.managed_endpoint_id
                endpoint = session.get(ManagedEndpointRecord, snapshot.managed_endpoint_id)
                if endpoint and credential.organization_id:
                    endpoint.organization_id = credential.organization_id
                session.commit()
            elif credential and credential.managed_endpoint_id != snapshot.managed_endpoint_id:
                raise HTTPException(status.HTTP_409_CONFLICT, "Agent credential is bound to another endpoint.")
            events = detect_changes(session, snapshot)
            create_incidents_for_events(session, events)
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    return Response(REPLY, media_type="application/xml")
