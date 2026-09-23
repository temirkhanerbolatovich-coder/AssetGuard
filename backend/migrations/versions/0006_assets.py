"""Add organizations, assets and endpoint linkage.

Revision ID: 0006_assets
Revises: 0005_incidents_history
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_assets"
down_revision = "0005_incidents_history"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("organizations", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id", name="pk_organizations"), sa.UniqueConstraint("name", name="uq_organizations_name"))
    op.create_table("assets", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("inventory_number", sa.String(128), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("asset_type", sa.String(16), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("room", sa.String(255), nullable=True), sa.Column("notes", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("asset_type IN ('Desktop', 'Laptop', 'Other')", name="ck_assets_type"), sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id", name="pk_assets"), sa.UniqueConstraint("organization_id", "inventory_number", name="uq_assets_org_inventory"))
    op.add_column("managed_endpoints", sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_managed_endpoints_asset", "managed_endpoints", "assets", ["asset_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_managed_endpoints_asset", "managed_endpoints", ["asset_id"])

def downgrade() -> None:
    op.drop_index("ix_managed_endpoints_asset", table_name="managed_endpoints"); op.drop_constraint("fk_managed_endpoints_asset", "managed_endpoints", type_="foreignkey"); op.drop_column("managed_endpoints", "asset_id"); op.drop_table("assets"); op.drop_table("organizations")
