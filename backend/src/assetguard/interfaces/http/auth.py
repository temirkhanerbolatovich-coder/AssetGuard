from datetime import UTC, datetime
import secrets
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.admin_assets import require_admin
from assetguard.modules.identity.auth import AuthPrincipal, create_session, hash_password, revoke_session_token, verify_password
from assetguard.modules.identity.models import AgentCredentialRecord, AuthSessionRecord, UserRecord

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


@router.post("/auth/login")
def login(body: LoginBody, session: Annotated[Session, Depends(get_session)]):
    user = session.scalar(select(UserRecord).where(UserRecord.username == body.username))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password.")
    return {"access_token": create_session(session, user), "token_type": "assetguard", "expires_in": 43200, "role": user.role}


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
