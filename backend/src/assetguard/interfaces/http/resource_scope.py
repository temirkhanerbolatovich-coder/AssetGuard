"""Authorization-aware lookup helpers for HTTP resources."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from assetguard.modules.assets.models import AssetRecord
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.identity.location_access import permitted_room_ids, require_room_access
from assetguard.modules.snapshots.models import ManagedEndpointRecord


def scoped_endpoint(
    session: Session,
    endpoint_id: UUID,
    principal: AuthPrincipal,
) -> ManagedEndpointRecord:
    """Return an endpoint only when it is visible to the current principal."""
    endpoint = session.get(ManagedEndpointRecord, endpoint_id)
    if not endpoint or (
        principal.organization_id and endpoint.organization_id != principal.organization_id
    ):
        raise HTTPException(404, "Endpoint was not found.")
    if endpoint.asset_id:
        asset = session.get(AssetRecord, endpoint.asset_id)
        require_room_access(session, asset.room_id if asset else None, principal)
    elif permitted_room_ids(session, principal) is not None:
        raise HTTPException(404, "Endpoint was not found.")
    return endpoint
