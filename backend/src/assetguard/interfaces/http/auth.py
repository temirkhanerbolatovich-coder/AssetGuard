from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.admin_assets import require_admin
from assetguard.modules.identity.auth import create_session, hash_password, revoke_session_token, verify_password
from assetguard.modules.identity.models import AuthSessionRecord, UserRecord

router = APIRouter(tags=["authentication"])


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=12, max_length=512)


class UserCreate(LoginBody):
    role: Literal["ADMIN", "VIEWER"]


class UserUpdate(BaseModel):
    role: Literal["ADMIN", "VIEWER"] | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=512)


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


@router.get("/admin/users", dependencies=[Depends(require_admin)])
def users(session: Annotated[Session, Depends(get_session)]):
    return [{"id": str(user.id), "username": user.username, "role": user.role, "active": user.is_active, "created_at": user.created_at} for user in session.scalars(select(UserRecord).order_by(UserRecord.username))]


@router.post("/admin/users", dependencies=[Depends(require_admin)], status_code=201)
def create_user(body: UserCreate, session: Annotated[Session, Depends(get_session)]):
    if session.scalar(select(UserRecord).where(UserRecord.username == body.username)):
        raise HTTPException(409, "Username already exists.")
    user = UserRecord(username=body.username, password_hash=hash_password(body.password), role=body.role, is_active=True, created_at=datetime.now(UTC))
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"id": str(user.id), "username": user.username, "role": user.role, "active": user.is_active}


@router.patch("/admin/users/{user_id}", dependencies=[Depends(require_admin)])
def update_user(user_id: UUID, body: UserUpdate, session: Annotated[Session, Depends(get_session)]):
    user = session.get(UserRecord, user_id)
    if not user:
        raise HTTPException(404, "User was not found.")
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


@router.get("/admin/sessions", dependencies=[Depends(require_admin)])
def sessions(session: Annotated[Session, Depends(get_session)]):
    rows = session.execute(
        select(AuthSessionRecord, UserRecord.username)
        .join(UserRecord, UserRecord.id == AuthSessionRecord.user_id)
        .order_by(AuthSessionRecord.expires_at.desc())
    )
    return [{
        "id": str(auth_session.id), "username": username,
        "created_at": auth_session.created_at, "expires_at": auth_session.expires_at,
    } for auth_session, username in rows]


@router.delete("/admin/sessions/{session_id}", status_code=204, dependencies=[Depends(require_admin)])
def revoke_session(session_id: UUID, session: Annotated[Session, Depends(get_session)]):
    auth_session = session.get(AuthSessionRecord, session_id)
    if not auth_session:
        raise HTTPException(404, "Session was not found.")
    session.delete(auth_session)
    session.commit()
    return Response(status_code=204)
