"""Add named users, roles, and revocable API sessions.

Revision ID: 0008_users_and_sessions
Revises: 0007_complete_mvp_foundation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_users_and_sessions"
down_revision = "0007_complete_mvp_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('ADMIN', 'VIEWER')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_auth_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
    )
    op.create_index("ix_auth_sessions_expires", "auth_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_expires", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("users")
