from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from assetguard.modules.inventory.models import Base


class UserRecord(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(128), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16))
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthSessionRecord(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentCredentialRecord(Base):
    __tablename__ = "agent_credentials"
    __table_args__ = (
        Index(
            "uq_agent_credentials_active_endpoint",
            "managed_endpoint_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND managed_endpoint_id IS NOT NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(128), unique=True)
    secret_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    managed_endpoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("managed_endpoints.id"), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentReenrolmentRecord(Base):
    __tablename__ = "agent_reenrolments"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    credential_secret_hash: Mapped[str] = mapped_column(Text)
    identifier_type: Mapped[str] = mapped_column(String(32))
    identifier_value: Mapped[str] = mapped_column(String(512))
    computer_name: Mapped[str] = mapped_column(String(255))
    installer_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    managed_endpoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("managed_endpoints.id"), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    credential_id: Mapped[UUID | None] = mapped_column(ForeignKey("agent_credentials.id"), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)


class LocationAccessRecord(Base):
    __tablename__ = "location_access"
    __table_args__ = (UniqueConstraint("user_id", "scope_type", "scope_id", name="uq_location_access_scope"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    scope_type: Mapped[str] = mapped_column(String(16))  # BUILDING, FLOOR, ROOM
    scope_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    permission: Mapped[str] = mapped_column(String(16))  # VIEWER or EDITOR
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
