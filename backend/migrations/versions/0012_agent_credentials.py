"""Add per-agent credentials for native GLPI inventory.

Revision ID: 0012_agent_credentials
Revises: 0011_vision_asset_link
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_agent_credentials"
down_revision = "0011_vision_asset_link"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "agent_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("secret_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("managed_endpoint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'REVOKED')", name="ck_agent_credentials_status"),
        sa.ForeignKeyConstraint(["managed_endpoint_id"], ["managed_endpoints.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_credentials"),
        sa.UniqueConstraint("username", name="uq_agent_credentials_username"),
        sa.UniqueConstraint("managed_endpoint_id", name="uq_agent_credentials_endpoint"),
    )

def downgrade() -> None:
    op.drop_table("agent_credentials")
