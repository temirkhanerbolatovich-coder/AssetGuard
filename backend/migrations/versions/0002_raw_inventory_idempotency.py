"""Add transport idempotency to raw inventory ingestion.

Revision ID: 0002_raw_inventory_idempotency
Revises: 0001_raw_inventories
Create Date: 2026-09-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_raw_inventory_idempotency"
down_revision = "0001_raw_inventories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "raw_inventories",
        sa.Column("ingest_idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_raw_inventories_ingest_idempotency_key",
        "raw_inventories",
        ["ingest_idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_raw_inventories_ingest_idempotency_key",
        "raw_inventories",
        type_="unique",
    )
    op.drop_column("raw_inventories", "ingest_idempotency_key")

