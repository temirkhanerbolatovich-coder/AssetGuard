from datetime import UTC, datetime, timedelta
import secrets
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.authorization import require_admin, require_viewer
from assetguard.modules.identity.auth import AuthPrincipal, create_session, hash_password, revoke_session_token, token_hash, verify_password
from assetguard.modules.identity.location_access import permitted_room_ids
from assetguard.modules.identity.models import AgentCredentialRecord, AgentReenrolmentRecord, AuthSessionRecord, UserRecord
from assetguard.modules.snapshots.models import EndpointIdentifierRecord, ManagedEndpointRecord
from assetguard.modules.snapshots.normalizer import normalize_identifier

router = APIRouter(tags=["authentication"])


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=12, max_length=512)


class UserCreate(LoginBody):
    role: Literal["ADMIN", "VIEWER", "LOCATION_MANAGER", "INVENTORY_CLERK"]
    organization_id: UUID | None = None


class UserUpdate(BaseModel):
    role: Literal["ADMIN", "VIEWER", "LOCATION_MANAGER", "INVENTORY_CLERK"] | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=512)


class AgentCredentialCreate(BaseModel):
    organization_id: UUID | None = None


class AgentReenrolmentCreate(BaseModel):
    identifier_type: Literal["SMBIOS_UUID", "CHASSIS_SERIAL", "BIOS_SERIAL", "MOTHERBOARD_SERIAL"]
    identifier_value: str = Field(min_length=4, max_length=512)
    computer_name: str = Field(min_length=1, max_length=255)
    installer_version: str = Field(pattern=r"^\d+\.\d+\.\d+$", max_length=32)


@router.post("/auth/login")
def login(body: LoginBody, session: Annotated[Session, Depends(get_session)]):
    user = session.scalar(select(UserRecord).where(UserRecord.username == body.username))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password.")
    return {"access_token": create_session(session, user), "token_type": "assetguard", "expires_in": 43200, "role": user.role}


@router.get("/auth/me")
def current_user(principal: Annotated[AuthPrincipal, Depends(require_viewer)], session: Annotated[Session, Depends(get_session)]):
    editable_rooms = permitted_room_ids(session, principal, write=True)
    if principal.role != "ADMIN" and principal.user_id is None:
        editable_rooms = set()
    return {
        "id": str(principal.user_id) if principal.user_id else None,
        "username": principal.username,
        "role": principal.role,
        "organization_id": str(principal.organization_id) if principal.organization_id else None,
        "editable_room_ids": None if principal.role == "ADMIN" else [str(room_id) for room_id in (editable_rooms or set())],
    }


@router.post("/auth/logout", status_code=204)
def logout(
    token: Annotated[str | None, Header(alias="X-AssetGuard-Admin-Token")] = None,
    session: Session = Depends(get_session),
):
    if not token or not revoke_session_token(session, token):
        raise HTTPException(401, "The session token is invalid or already revoked.")
    return Response(status_code=204)


def _tenant_filter(query, model, principal: AuthPrincipal):
    """Apply the caller's organization boundary; a legacy global admin remains platform-scoped."""
    return query.where(model.organization_id == principal.organization_id) if principal.organization_id else query


def _require_same_tenant(organization_id: UUID | None, principal: AuthPrincipal, detail: str) -> None:
    if principal.organization_id and organization_id != principal.organization_id:
        raise HTTPException(404, detail)


def _reenrolment_status(item: AgentReenrolmentRecord, now: datetime) -> str:
    if item.status == "PENDING" and item.expires_at <= now:
        return "EXPIRED"
    return item.status


@router.post("/agent/re-enrolments", status_code=202)
def request_agent_reenrolment(body: AgentReenrolmentCreate, session: Annotated[Session, Depends(get_session)]):
    normalized = normalize_identifier(body.identifier_value)
    if normalized is None:
        raise HTTPException(422, "The hardware identifier is not suitable for re-enrolment.")
    computer_name = body.computer_name.strip()
    if not computer_name:
        raise HTTPException(422, "Computer name must not be blank.")
    identifier = session.scalar(select(EndpointIdentifierRecord).where(
        EndpointIdentifierRecord.identifier_type == body.identifier_type,
        EndpointIdentifierRecord.normalized_value == normalized,
        EndpointIdentifierRecord.is_active.is_(True),
    ))
    endpoint = session.get(ManagedEndpointRecord, identifier.managed_endpoint_id) if identifier else None
    claim_token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    request = AgentReenrolmentRecord(
        token_hash=token_hash(claim_token), credential_secret_hash=hash_password(claim_token),
        identifier_type=body.identifier_type, identifier_value=normalized,
        computer_name=computer_name, installer_version=body.installer_version,
        status="PENDING", managed_endpoint_id=endpoint.id if endpoint else None,
        organization_id=endpoint.organization_id if endpoint else None, credential_id=None,
        requested_at=now, expires_at=now + timedelta(minutes=30), decided_at=None, decided_by=None,
    )
    session.add(request)
    session.commit()
    return {"id": str(request.id), "claim_token": claim_token, "status": "PENDING", "expires_at": request.expires_at}


@router.get("/agent/re-enrolments/{request_id}")
def agent_reenrolment_status(
    request_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    claim_token: Annotated[str | None, Header(alias="X-AssetGuard-Reenrolment-Token", min_length=32, max_length=128)] = None,
):
    item = session.get(AgentReenrolmentRecord, request_id)
    if not item or not claim_token or not secrets.compare_digest(item.token_hash, token_hash(claim_token)):
        raise HTTPException(404, "Re-enrolment request was not found.")
    current_status = _reenrolment_status(item, datetime.now(UTC))
    response = {"id": str(item.id), "status": current_status, "expires_at": item.expires_at}
    if current_status == "APPROVED" and item.credential_id:
        credential = session.get(AgentCredentialRecord, item.credential_id)
        if credential and credential.status == "ACTIVE":
            response["agent_username"] = credential.username
    return response


@router.get("/admin/users")
def users(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    query = _tenant_filter(select(UserRecord).order_by(UserRecord.username), UserRecord, principal)
    return [{"id": str(user.id), "username": user.username, "role": user.role, "organization_id": str(user.organization_id) if user.organization_id else None, "active": user.is_active, "created_at": user.created_at} for user in session.scalars(query)]


@router.post("/admin/users", status_code=201)
def create_user(body: UserCreate, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    if session.scalar(select(UserRecord).where(UserRecord.username == body.username)):
        raise HTTPException(409, "Username already exists.")
    if principal.organization_id and body.organization_id not in (None, principal.organization_id):
        raise HTTPException(403, "A tenant administrator can create users only in their own organization.")
    organization_id = principal.organization_id or body.organization_id
    user = UserRecord(username=body.username, password_hash=hash_password(body.password), role=body.role, organization_id=organization_id, is_active=True, created_at=datetime.now(UTC))
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"id": str(user.id), "username": user.username, "role": user.role, "organization_id": str(user.organization_id) if user.organization_id else None, "active": user.is_active}


@router.patch("/admin/users/{user_id}")
def update_user(user_id: UUID, body: UserUpdate, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    user = session.get(UserRecord, user_id)
    if not user:
        raise HTTPException(404, "User was not found.")
    _require_same_tenant(user.organization_id, principal, "User was not found.")
    if body.role is not None:
        user.role = body.role
    if body.active is not None:
        user.is_active = body.active
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    session.commit()
    if body.active is False or body.password is not None:
        for auth_session in session.scalars(select(AuthSessionRecord).where(AuthSessionRecord.user_id == user.id)):
            session.delete(auth_session)
        session.commit()
    return {"id": str(user.id), "username": user.username, "role": user.role, "active": user.is_active}


@router.get("/admin/sessions")
def sessions(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    query = (
        select(AuthSessionRecord, UserRecord.username)
        .join(UserRecord, UserRecord.id == AuthSessionRecord.user_id)
        .order_by(AuthSessionRecord.expires_at.desc())
    )
    rows = session.execute(_tenant_filter(query, UserRecord, principal))
    return [{
        "id": str(auth_session.id), "username": username,
        "created_at": auth_session.created_at, "expires_at": auth_session.expires_at,
    } for auth_session, username in rows]


@router.delete("/admin/sessions/{session_id}", status_code=204)
def revoke_session(session_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    auth_session = session.get(AuthSessionRecord, session_id)
    if not auth_session:
        raise HTTPException(404, "Session was not found.")
    user = session.get(UserRecord, auth_session.user_id)
    _require_same_tenant(user.organization_id if user else None, principal, "Session was not found.")
    session.delete(auth_session)
    session.commit()
    return Response(status_code=204)


@router.get("/admin/agent-credentials")
def agent_credentials(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    query = _tenant_filter(select(AgentCredentialRecord).order_by(AgentCredentialRecord.issued_at.desc()), AgentCredentialRecord, principal)
    return [{
        "id": str(item.id), "username": item.username, "status": item.status,
        "endpoint_id": str(item.managed_endpoint_id) if item.managed_endpoint_id else None,
        "issued_at": item.issued_at, "revoked_at": item.revoked_at,
    } for item in session.scalars(query)]


@router.post("/admin/agent-credentials", status_code=201)
def create_agent_credential(session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)], body: AgentCredentialCreate | None = None):
    # The raw secret is returned exactly once and is never persisted in plaintext.
    username = f"ag-{secrets.token_hex(8)}"
    secret = secrets.token_urlsafe(32)
    requested_organization = body.organization_id if body else None
    if principal.organization_id and requested_organization not in (None, principal.organization_id):
        raise HTTPException(403, "A tenant administrator can issue credentials only for their own organization.")
    credential = AgentCredentialRecord(
        username=username, secret_hash=hash_password(secret), status="ACTIVE",
        issued_at=datetime.now(UTC), revoked_at=None, managed_endpoint_id=None, organization_id=principal.organization_id or requested_organization,
    )
    session.add(credential)
    session.commit()
    return {"id": str(credential.id), "username": username, "secret": secret, "status": "ACTIVE"}


@router.post("/admin/agent-credentials/{credential_id}/revoke")
def revoke_agent_credential(credential_id: UUID, session: Annotated[Session, Depends(get_session)], principal: Annotated[AuthPrincipal, Depends(require_admin)]):
    credential = session.get(AgentCredentialRecord, credential_id)
    if not credential:
        raise HTTPException(404, "Agent credential was not found.")
    _require_same_tenant(credential.organization_id, principal, "Agent credential was not found.")
    if credential.status != "REVOKED":
        credential.status = "REVOKED"
        credential.revoked_at = datetime.now(UTC)
        session.commit()
    return {"id": str(credential.id), "status": credential.status, "revoked_at": credential.revoked_at}


@router.get("/admin/agent-re-enrolments")
def agent_reenrolments(
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_admin)],
):
    query = select(AgentReenrolmentRecord).order_by(AgentReenrolmentRecord.requested_at.desc()).limit(100)
    if principal.organization_id:
        query = query.where(AgentReenrolmentRecord.organization_id == principal.organization_id)
    now = datetime.now(UTC)
    result = []
    for item in session.scalars(query):
        endpoint = session.get(ManagedEndpointRecord, item.managed_endpoint_id) if item.managed_endpoint_id else None
        result.append({
            "id": str(item.id), "status": _reenrolment_status(item, now),
            "identifier_type": item.identifier_type, "identifier_value": item.identifier_value,
            "computer_name": item.computer_name, "installer_version": item.installer_version,
            "endpoint_id": str(item.managed_endpoint_id) if item.managed_endpoint_id else None,
            "endpoint_hostname": endpoint.hostname if endpoint else None,
            "requested_at": item.requested_at, "expires_at": item.expires_at,
            "decided_at": item.decided_at, "decided_by": item.decided_by,
        })
    return result


def _pending_reenrolment_for_admin(
    request_id: UUID, session: Session, principal: AuthPrincipal,
) -> AgentReenrolmentRecord:
    item = session.get(AgentReenrolmentRecord, request_id)
    if not item:
        raise HTTPException(404, "Re-enrolment request was not found.")
    _require_same_tenant(item.organization_id, principal, "Re-enrolment request was not found.")
    if _reenrolment_status(item, datetime.now(UTC)) == "EXPIRED":
        raise HTTPException(409, "Re-enrolment request has expired.")
    if item.status != "PENDING":
        raise HTTPException(409, "Re-enrolment request has already been decided.")
    return item


@router.post("/admin/agent-re-enrolments/{request_id}/approve")
def approve_agent_reenrolment(
    request_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_admin)],
):
    item = _pending_reenrolment_for_admin(request_id, session, principal)
    if not item.managed_endpoint_id:
        raise HTTPException(409, "No existing endpoint matches this hardware identifier.")
    now = datetime.now(UTC)
    for credential in session.scalars(select(AgentCredentialRecord).where(
        AgentCredentialRecord.managed_endpoint_id == item.managed_endpoint_id,
        AgentCredentialRecord.status == "ACTIVE",
    )):
        credential.status = "REVOKED"
        credential.revoked_at = now
    session.flush()
    credential = AgentCredentialRecord(
        username=f"ag-{secrets.token_hex(8)}", secret_hash=item.credential_secret_hash,
        status="ACTIVE", issued_at=now, revoked_at=None,
        managed_endpoint_id=item.managed_endpoint_id, organization_id=item.organization_id,
    )
    session.add(credential)
    session.flush()
    item.status = "APPROVED"
    item.credential_id = credential.id
    item.decided_at = now
    item.decided_by = principal.username
    session.commit()
    return {"id": str(item.id), "status": item.status, "endpoint_id": str(item.managed_endpoint_id)}


@router.post("/admin/agent-re-enrolments/{request_id}/reject")
def reject_agent_reenrolment(
    request_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    principal: Annotated[AuthPrincipal, Depends(require_admin)],
):
    item = _pending_reenrolment_for_admin(request_id, session, principal)
    item.status = "REJECTED"
    item.decided_at = datetime.now(UTC)
    item.decided_by = principal.username
    session.commit()
    return {"id": str(item.id), "status": item.status}
