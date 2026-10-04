"""Durable Telegram outbox; records are committed with their source incident."""
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from assetguard.modules.inventory.models import Base


class TelegramNotificationRecord(Base):
    __tablename__ = "telegram_notifications"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'SENT')", name="ck_telegram_notifications_status"),
        CheckConstraint("attempts >= 0", name="ck_telegram_notifications_attempts"),
        Index("ix_telegram_notifications_due", "organization_id", "status", "next_attempt_at"),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_key: Mapped[str] = mapped_column(String(160), unique=True)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    room_id: Mapped[UUID | None] = mapped_column(ForeignKey("location_rooms.id", ondelete="RESTRICT"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
