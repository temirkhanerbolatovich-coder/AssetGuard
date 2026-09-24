"""Scope Vision rooms to organisations.

Revision ID: 0015_vision_tenant_scope
Revises: 0014_endpoint_tenant_scope
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "0015_vision_tenant_scope"
down_revision = "0014_endpoint_tenant_scope"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.add_column("vision_rooms", sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_vision_rooms_organization", "vision_rooms", "organizations", ["organization_id"], ["id"], ondelete="RESTRICT")
    op.drop_constraint("uq_vision_rooms_name", "vision_rooms", type_="unique")
    op.create_unique_constraint("uq_vision_rooms_organization_name", "vision_rooms", ["organization_id", "name"])
def downgrade() -> None:
    op.drop_constraint("uq_vision_rooms_organization_name", "vision_rooms", type_="unique")
    op.create_unique_constraint("uq_vision_rooms_name", "vision_rooms", ["name"])
    op.drop_constraint("fk_vision_rooms_organization", "vision_rooms", type_="foreignkey")
    op.drop_column("vision_rooms", "organization_id")
