"""Create immutable raw inventory storage.

Revision ID: 0001_raw_inventories
Revises:
Create Date: 2026-09-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_raw_inventories"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_inventories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        # Endpoint resolution follows raw preservation and is therefore nullable at ingest.
        sa.Column("managed_endpoint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "inventory_type",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'UNKNOWN'"),
        ),
        sa.Column(
            "processing_status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'RECEIVED'"),
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "inventory_type IN ('FULL', 'PARTIAL', 'UNKNOWN')",
            name="ck_raw_inventories_inventory_type",
        ),
        sa.CheckConstraint(
            "processing_status IN ('RECEIVED', 'PROCESSED', 'FAILED')",
            name="ck_raw_inventories_processing_status",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_raw_inventories"),
    )
    op.create_index(
        "ix_raw_inventories_received_at",
        "raw_inventories",
        ["received_at"],
    )
    op.create_index(
        "ix_raw_inventories_source_payload_hash",
        "raw_inventories",
        ["source", "payload_hash"],
    )
    op.execute(
        """
        CREATE FUNCTION assetguard_prevent_raw_inventory_mutation()
        RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'RawInventory records are append-only';
          END IF;

          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.source IS DISTINCT FROM OLD.source
             OR NEW.source_version IS DISTINCT FROM OLD.source_version
             OR NEW.schema_version IS DISTINCT FROM OLD.schema_version
             OR NEW.received_at IS DISTINCT FROM OLD.received_at
             OR NEW.payload_hash IS DISTINCT FROM OLD.payload_hash
             OR NEW.payload IS DISTINCT FROM OLD.payload
             OR NEW.inventory_type IS DISTINCT FROM OLD.inventory_type
          THEN
            RAISE EXCEPTION 'RawInventory evidence fields are immutable';
          END IF;

          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_raw_inventories_immutable
        BEFORE UPDATE OR DELETE ON raw_inventories
        FOR EACH ROW EXECUTE FUNCTION assetguard_prevent_raw_inventory_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_raw_inventories_immutable ON raw_inventories")
    op.execute("DROP FUNCTION IF EXISTS assetguard_prevent_raw_inventory_mutation()")
    op.drop_index("ix_raw_inventories_source_payload_hash", table_name="raw_inventories")
    op.drop_index("ix_raw_inventories_received_at", table_name="raw_inventories")
    op.drop_table("raw_inventories")

