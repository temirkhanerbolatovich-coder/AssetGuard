"""Scope managed endpoints to an organisation.

Revision ID: 0014_endpoint_tenant_scope
Revises: 0013_tenant_foundation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_endpoint_tenant_scope"
down_revision = "0013_tenant_foundation"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("managed_endpoints", sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_endpoints_organization", "managed_endpoints", "organizations", ["organization_id"], ["id"], ondelete="RESTRICT")
    op.execute("UPDATE managed_endpoints e SET organization_id = a.organization_id FROM assets a WHERE e.asset_id = a.id")

def downgrade() -> None:
    op.drop_constraint("fk_endpoints_organization", "managed_endpoints", type_="foreignkey")
    op.drop_column("managed_endpoints", "organization_id")
