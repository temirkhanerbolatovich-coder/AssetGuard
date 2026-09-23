"""Create endpoint and normalized hardware snapshot tables.

Revision ID: 0003_endpoints_and_hardware_snapshots
Revises: 0002_raw_inventory_idempotency
Create Date: 2026-09-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_endpoint_snapshots"
down_revision = "0002_raw_inventory_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "managed_endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_agent_id", sa.String(255), nullable=True),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('ONLINE', 'OFFLINE', 'REQUIRES_VERIFICATION', 'IDENTITY_CONFLICT')",
            name="ck_managed_endpoints_status",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_managed_endpoints"),
    )
    op.create_index("ix_managed_endpoints_source_agent_id", "managed_endpoints", ["source", "source_agent_id"])

    op.create_table(
        "endpoint_identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("managed_endpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_type", sa.String(32), nullable=False),
        sa.Column("raw_value", sa.String(512), nullable=False),
        sa.Column("normalized_value", sa.String(512), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "confidence IN ('HIGH', 'MEDIUM', 'LOW', 'UNKNOWN')",
            name="ck_endpoint_identifiers_confidence",
        ),
        sa.ForeignKeyConstraint(["managed_endpoint_id"], ["managed_endpoints.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_endpoint_identifiers"),
        sa.UniqueConstraint("identifier_type", "normalized_value", name="uq_endpoint_identifiers_type_normalized"),
    )
    op.create_index("ix_endpoint_identifiers_endpoint", "endpoint_identifiers", ["managed_endpoint_id"])
    op.create_foreign_key(
        "fk_raw_inventories_managed_endpoint",
        "raw_inventories",
        "managed_endpoints",
        ["managed_endpoint_id"], ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "hardware_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("managed_endpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_inventory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_type", sa.String(16), nullable=False),
        sa.Column("completeness", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalizer_version", sa.String(32), nullable=False),
        sa.CheckConstraint("snapshot_type IN ('FULL', 'PARTIAL')", name="ck_hardware_snapshots_type"),
        sa.ForeignKeyConstraint(["managed_endpoint_id"], ["managed_endpoints.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["raw_inventory_id"], ["raw_inventories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_hardware_snapshots"),
        sa.UniqueConstraint("raw_inventory_id", name="uq_hardware_snapshots_raw_inventory"),
    )
    op.create_index("ix_hardware_snapshots_endpoint_captured", "hardware_snapshots", ["managed_endpoint_id", "captured_at"])

    op.create_table(
        "component_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_type", sa.String(32), nullable=False),
        sa.Column("canonical_serial", sa.String(512), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("model", sa.String(512), nullable=True),
        sa.Column("part_number", sa.String(255), nullable=True),
        sa.Column("identity_confidence", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("identity_confidence IN ('HIGH', 'MEDIUM', 'LOW', 'UNKNOWN')", name="ck_component_identities_confidence"),
        sa.PrimaryKeyConstraint("id", name="pk_component_identities"),
        sa.UniqueConstraint("component_type", "canonical_serial", name="uq_component_identities_type_serial"),
    )
    op.create_table(
        "component_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hardware_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_type", sa.String(32), nullable=False),
        sa.Column("component_identity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("model", sa.String(512), nullable=True),
        sa.Column("serial_number", sa.String(512), nullable=True),
        sa.Column("part_number", sa.String(255), nullable=True),
        sa.Column("capacity", sa.BigInteger(), nullable=True),
        sa.Column("slot", sa.String(255), nullable=True),
        sa.Column("source_key", sa.String(512), nullable=True),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("component_type IN ('CPU', 'MOTHERBOARD', 'RAM', 'STORAGE', 'GPU', 'NETWORK', 'MONITOR')", name="ck_component_observations_type"),
        sa.CheckConstraint("confidence IN ('HIGH', 'MEDIUM', 'LOW', 'UNKNOWN')", name="ck_component_observations_confidence"),
        sa.ForeignKeyConstraint(["hardware_snapshot_id"], ["hardware_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["component_identity_id"], ["component_identities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_component_observations"),
    )
    op.create_index("ix_component_observations_snapshot", "component_observations", ["hardware_snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_component_observations_snapshot", table_name="component_observations")
    op.drop_table("component_observations")
    op.drop_table("component_identities")
    op.drop_index("ix_hardware_snapshots_endpoint_captured", table_name="hardware_snapshots")
    op.drop_table("hardware_snapshots")
    op.drop_constraint("fk_raw_inventories_managed_endpoint", "raw_inventories", type_="foreignkey")
    op.drop_index("ix_endpoint_identifiers_endpoint", table_name="endpoint_identifiers")
    op.drop_table("endpoint_identifiers")
    op.drop_index("ix_managed_endpoints_source_agent_id", table_name="managed_endpoints")
    op.drop_table("managed_endpoints")
