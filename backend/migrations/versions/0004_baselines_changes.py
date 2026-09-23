"""Add explicit baselines and explainable change events.

Revision ID: 0004_baselines_changes
Revises: 0003_endpoint_snapshots
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_baselines_changes"
down_revision = "0003_endpoint_snapshots"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "baselines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("managed_endpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hardware_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE', 'SUPERSEDED', 'REJECTED')", name="ck_baselines_status"),
        sa.ForeignKeyConstraint(["managed_endpoint_id"], ["managed_endpoints.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["hardware_snapshot_id"], ["hardware_snapshots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_baselines"),
        sa.UniqueConstraint("hardware_snapshot_id", name="uq_baselines_snapshot"),
    )
    op.create_index("uq_baselines_one_active_endpoint", "baselines", ["managed_endpoint_id"], unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))
    op.create_table(
        "change_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("managed_endpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_type", sa.String(32), nullable=False),
        sa.Column("previous_observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detector_version", sa.String(32), nullable=False),
        sa.Column("dedup_key", sa.String(64), nullable=False),
        sa.CheckConstraint("component_type IN ('RAM', 'STORAGE')", name="ck_change_events_component_type"),
        sa.CheckConstraint("event_type IN ('COMPONENT_ADDED', 'COMPONENT_REMOVED')", name="ck_change_events_type"),
        sa.CheckConstraint("confidence IN ('HIGH', 'MEDIUM', 'LOW', 'UNKNOWN')", name="ck_change_events_confidence"),
        sa.CheckConstraint("status IN ('OPEN', 'RESOLVED', 'DISMISSED')", name="ck_change_events_status"),
        sa.ForeignKeyConstraint(["managed_endpoint_id"], ["managed_endpoints.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["baseline_id"], ["baselines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["baseline_snapshot_id"], ["hardware_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["current_snapshot_id"], ["hardware_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["previous_observation_id"], ["component_observations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["current_observation_id"], ["component_observations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_change_events"),
        sa.UniqueConstraint("dedup_key", name="uq_change_events_dedup_key"),
    )
    op.create_index("ix_change_events_endpoint_status", "change_events", ["managed_endpoint_id", "status"])

def downgrade() -> None:
    op.drop_index("ix_change_events_endpoint_status", table_name="change_events")
    op.drop_table("change_events")
    op.drop_index("uq_baselines_one_active_endpoint", table_name="baselines")
    op.drop_table("baselines")
