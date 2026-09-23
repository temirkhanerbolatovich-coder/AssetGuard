from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.modules.identity.models import AuthSessionRecord, UserRecord

ITERATIONS = 310_000


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    username: str
    role: str
    session_id: UUID | None


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt), int(rounds))
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(expected))
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(session: Session, user: UserRecord, hours: int = 12) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session.add(AuthSessionRecord(
        user_id=user.id, token_hash=token_hash(token), created_at=now,
        expires_at=now + timedelta(hours=hours),
    ))
    session.commit()
    return token


def session_principal(session: Session, token: str) -> AuthPrincipal | None:
    record = session.scalar(select(AuthSessionRecord).where(
        AuthSessionRecord.token_hash == token_hash(token),
        AuthSessionRecord.expires_at > datetime.now(UTC),
    ))
    if not record:
        return None
    user = session.get(UserRecord, record.user_id)
    if not user or not user.is_active:
        return None
    return AuthPrincipal(username=user.username, role=user.role, session_id=record.id)


def session_role(session: Session, token: str) -> str | None:
    principal = session_principal(session, token)
    return principal.role if principal else None


def revoke_session_token(session: Session, token: str) -> bool:
    record = session.scalar(select(AuthSessionRecord).where(
        AuthSessionRecord.token_hash == token_hash(token),
    ))
    if record is None:
        return False
    session.delete(record)
    session.commit()
    return True
