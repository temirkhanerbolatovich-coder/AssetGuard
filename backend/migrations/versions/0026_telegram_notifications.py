"""Persist Telegram notifications with incidents.

Revision ID: 0026_telegram_notifications
Revises: 0025_agent_reenrolment
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0026_telegram_notifications"
down_revision = "0025_agent_reenrolment"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "telegram_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_key", sa.String(160), nullable=False, unique=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="RESTRICT")),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("location_rooms.id", ondelete="RESTRICT")),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("telegram_message_id", sa.BigInteger()),
        sa.Column("last_error_code", sa.String(64)),
        sa.CheckConstraint("status IN ('PENDING', 'SENT')", name="ck_telegram_notifications_status"),
        sa.CheckConstraint("attempts >= 0", name="ck_telegram_notifications_attempts"),
    )
    op.create_index("ix_telegram_notifications_due", "telegram_notifications", ["organization_id", "status", "next_attempt_at"])


def downgrade():
    op.drop_index("ix_telegram_notifications_due", table_name="telegram_notifications")
    op.drop_table("telegram_notifications")
