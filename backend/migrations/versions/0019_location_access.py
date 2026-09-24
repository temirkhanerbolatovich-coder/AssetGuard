"""Add user access scopes for managed locations.

Revision ID: 0019_location_access
Revises: 0018_classify_imported_property
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0019_location_access"
down_revision = "0018_classify_imported_property"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("location_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("scope_type", sa.String(16), nullable=False), sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("permission", sa.String(16), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("user_id", "scope_type", "scope_id", name="uq_location_access_scope"), sa.CheckConstraint("scope_type IN ('BUILDING', 'FLOOR', 'ROOM')", name="ck_location_access_scope_type"), sa.CheckConstraint("permission IN ('VIEWER', 'EDITOR')", name="ck_location_access_permission"),
    )

def downgrade() -> None:
    op.drop_table("location_access")
