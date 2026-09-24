from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.modules.assets.models import BuildingRecord, FloorRecord, RoomRecord
from assetguard.modules.identity.auth import AuthPrincipal
from assetguard.modules.identity.models import LocationAccessRecord


def permitted_room_ids(session: Session, principal: AuthPrincipal, write: bool = False) -> set[UUID] | None:
    """None means organization-wide access; an empty set means no assigned rooms."""
    if principal.role == "ADMIN" or principal.user_id is None:
        return None
    permissions = {"EDITOR"} if write else {"VIEWER", "EDITOR"}
    grants = list(session.scalars(select(LocationAccessRecord).where(LocationAccessRecord.user_id == principal.user_id, LocationAccessRecord.permission.in_(permissions))))
    room_ids: set[UUID] = set()
    for grant in grants:
        if grant.scope_type == "ROOM": room_ids.add(grant.scope_id)
        elif grant.scope_type == "FLOOR": room_ids.update(session.scalars(select(RoomRecord.id).where(RoomRecord.floor_id == grant.scope_id)))
        elif grant.scope_type == "BUILDING":
            floor_ids = list(session.scalars(select(FloorRecord.id).where(FloorRecord.building_id == grant.scope_id)))
            if floor_ids: room_ids.update(session.scalars(select(RoomRecord.id).where(RoomRecord.floor_id.in_(floor_ids))))
    return room_ids


def require_room_access(session: Session, room_id: UUID | None, principal: AuthPrincipal, write: bool = False) -> None:
    allowed = permitted_room_ids(session, principal, write)
    if allowed is not None and (room_id is None or room_id not in allowed):
        from fastapi import HTTPException
        raise HTTPException(404, "Resource was not found.")
