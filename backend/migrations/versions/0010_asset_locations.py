"""Add building and floor to the asset location hierarchy.

Revision ID: 0010_asset_locations
Revises: 0009_vision_mvp
"""
from alembic import op
import sqlalchemy as sa


revision = "0010_asset_locations"
down_revision = "0009_vision_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("building", sa.String(255), nullable=True))
    op.add_column("assets", sa.Column("floor", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "floor")
    op.drop_column("assets", "building")
