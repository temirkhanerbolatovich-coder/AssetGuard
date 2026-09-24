"""Add organisation scope to users and agent credentials.

Revision ID: 0013_tenant_foundation
Revises: 0012_agent_credentials
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_tenant_foundation"
down_revision = "0012_agent_credentials"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("users", sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_users_organization", "users", "organizations", ["organization_id"], ["id"], ondelete="RESTRICT")
    op.add_column("agent_credentials", sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_agent_credentials_organization", "agent_credentials", "organizations", ["organization_id"], ["id"], ondelete="RESTRICT")

def downgrade() -> None:
    op.drop_constraint("fk_agent_credentials_organization", "agent_credentials", type_="foreignkey")
    op.drop_column("agent_credentials", "organization_id")
    op.drop_constraint("fk_users_organization", "users", type_="foreignkey")
    op.drop_column("users", "organization_id")
