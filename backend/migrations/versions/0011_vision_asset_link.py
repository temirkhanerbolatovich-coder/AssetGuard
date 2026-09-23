"""Link a physical Vision scan to an AssetGuard asset.

Revision ID: 0011_vision_asset_link
Revises: 0010_asset_locations
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_vision_asset_link"
down_revision = "0010_asset_locations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vision_scans", sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_vision_scans_asset_id_assets", "vision_scans", "assets", ["asset_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_vision_scans_asset", "vision_scans", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_vision_scans_asset", table_name="vision_scans")
    op.drop_constraint("fk_vision_scans_asset_id_assets", "vision_scans", type_="foreignkey")
    op.drop_column("vision_scans", "asset_id")
