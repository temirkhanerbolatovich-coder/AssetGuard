from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.admin_assets import require_admin
from assetguard.modules.identity.auth import create_session, hash_password, verify_password
from assetguard.modules.identity.models import UserRecord

router = APIRouter(tags=["authentication"])


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=12, max_length=512)


class UserCreate(LoginBody):
    role: Literal["ADMIN", "VIEWER"]


@router.post("/auth/login")
def login(body: LoginBody, session: Annotated[Session, Depends(get_session)]):
    user = session.scalar(select(UserRecord).where(UserRecord.username == body.username))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password.")
    return {"access_token": create_session(session, user), "token_type": "assetguard", "expires_in": 43200, "role": user.role}


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
