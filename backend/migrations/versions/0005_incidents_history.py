"""Add incident workflow and append-only endpoint history.

Revision ID: 0005_incidents_history
Revises: 0004_baselines_changes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_incidents_history"
down_revision = "0004_baselines_changes"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("incidents", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("managed_endpoint_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("change_event_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("severity", sa.String(16), nullable=False), sa.Column("title", sa.String(512), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True), sa.CheckConstraint("status IN ('OPEN', 'UNDER_REVIEW', 'RESOLVED', 'DISMISSED')", name="ck_incidents_status"), sa.ForeignKeyConstraint(["managed_endpoint_id"], ["managed_endpoints.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["change_event_id"], ["change_events.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id", name="pk_incidents"), sa.UniqueConstraint("change_event_id", name="uq_incidents_change_event"))
    op.create_index("ix_incidents_endpoint_status", "incidents", ["managed_endpoint_id", "status"])
    op.create_table("incident_decisions", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("classification", sa.String(32), nullable=False), sa.Column("comment", sa.Text(), nullable=True), sa.Column("actor", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("classification IN ('PLANNED_MAINTENANCE', 'UPGRADE', 'REPAIR', 'AUTHORIZED_CHANGE', 'COMPONENT_TRANSFER', 'UNKNOWN', 'REQUIRES_INVESTIGATION', 'FALSE_POSITIVE')", name="ck_incident_decisions_classification"), sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id", name="pk_incident_decisions"))
    op.create_table("endpoint_history_entries", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("managed_endpoint_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("related_entity_type", sa.String(64), nullable=False), sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False), sa.ForeignKeyConstraint(["managed_endpoint_id"], ["managed_endpoints.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id", name="pk_endpoint_history_entries"))
    op.create_index("ix_endpoint_history_endpoint_time", "endpoint_history_entries", ["managed_endpoint_id", "occurred_at"])
    op.execute("""CREATE FUNCTION assetguard_prevent_history_mutation() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'History entries are append-only'; END; $$ LANGUAGE plpgsql; CREATE TRIGGER trg_endpoint_history_immutable BEFORE UPDATE OR DELETE ON endpoint_history_entries FOR EACH ROW EXECUTE FUNCTION assetguard_prevent_history_mutation();""")

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_endpoint_history_immutable ON endpoint_history_entries")
    op.execute("DROP FUNCTION IF EXISTS assetguard_prevent_history_mutation()")
    op.drop_index("ix_endpoint_history_endpoint_time", table_name="endpoint_history_entries"); op.drop_table("endpoint_history_entries")
    op.drop_table("incident_decisions"); op.drop_index("ix_incidents_endpoint_status", table_name="incidents"); op.drop_table("incidents")
