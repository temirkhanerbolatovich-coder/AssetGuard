"""Separate individual IT assets from grouped school property.

Revision ID: 0017_asset_accounting_modes
Revises: 0016_location_hierarchy
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_asset_accounting_modes"
down_revision = "0016_location_hierarchy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("category", sa.String(32), nullable=False, server_default="IT"))
    op.add_column("assets", sa.Column("tracking_mode", sa.String(16), nullable=False, server_default="INDIVIDUAL"))
    op.add_column("assets", sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("assets", sa.Column("unit", sa.String(32), nullable=False, server_default="шт."))
    op.drop_constraint("ck_assets_type", "assets", type_="check")
    op.create_check_constraint("ck_assets_type", "assets", "asset_type IN ('Desktop', 'Laptop', 'Printer', 'Projector', 'Network', 'Furniture', 'Sports', 'Educational', 'Other')")
    op.create_check_constraint("ck_assets_category", "assets", "category IN ('IT', 'FURNITURE', 'SPORTS', 'EDUCATIONAL', 'OTHER')")
    op.create_check_constraint("ck_assets_tracking_mode", "assets", "tracking_mode IN ('INDIVIDUAL', 'GROUPED')")
    op.create_check_constraint("ck_assets_quantity", "assets", "quantity > 0")
    op.alter_column("assets", "category", server_default=None)
    op.alter_column("assets", "tracking_mode", server_default=None)
    op.alter_column("assets", "quantity", server_default=None)
    op.alter_column("assets", "unit", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_assets_quantity", "assets", type_="check")
    op.drop_constraint("ck_assets_tracking_mode", "assets", type_="check")
    op.drop_constraint("ck_assets_category", "assets", type_="check")
    op.drop_constraint("ck_assets_type", "assets", type_="check")
    op.create_check_constraint("ck_assets_type", "assets", "asset_type IN ('Desktop', 'Laptop', 'Other')")
    op.drop_column("assets", "unit")
    op.drop_column("assets", "quantity")
    op.drop_column("assets", "tracking_mode")
    op.drop_column("assets", "category")
