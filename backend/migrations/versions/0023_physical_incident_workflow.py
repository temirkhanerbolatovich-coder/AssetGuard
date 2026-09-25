"""Add incident workflow for physical room discrepancies.

Revision ID: 0023_physical_incident_workflow
Revises: 0022_room_physical_inspections
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0023_physical_incident_workflow"
down_revision = "0022_room_physical_inspections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "physical_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_type", sa.String(16), nullable=False),
        sa.Column("affected_quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("issue_type IN ('MISSING', 'DAMAGED')", name="ck_physical_incidents_issue_type"),
        sa.CheckConstraint("affected_quantity >= 1", name="ck_physical_incidents_affected_quantity"),
        sa.CheckConstraint("status IN ('OPEN', 'UNDER_REVIEW', 'RESOLVED')", name="ck_physical_incidents_status"),
        sa.CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH')", name="ck_physical_incidents_severity"),
        sa.ForeignKeyConstraint(["room_id"], ["location_rooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inspection_item_id"], ["room_inspection_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_physical_incidents"),
        sa.UniqueConstraint("inspection_item_id", name="uq_physical_incidents_inspection_item"),
    )
    op.create_index("ix_physical_incidents_room_status", "physical_incidents", ["room_id", "status"])
    op.create_index("ix_physical_incidents_asset_time", "physical_incidents", ["asset_id", "created_at"])
    op.create_table(
        "physical_incident_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('INVESTIGATE', 'MOVE', 'REPAIR', 'WRITE_OFF', 'FALSE_POSITIVE')",
            name="ck_physical_incident_decisions_action",
        ),
        sa.ForeignKeyConstraint(["incident_id"], ["physical_incidents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_physical_incident_decisions"),
    )
    op.create_index(
        "ix_physical_incident_decisions_incident_time",
        "physical_incident_decisions", ["incident_id", "created_at"],
    )
    op.execute(
        """
        CREATE FUNCTION assetguard_prevent_physical_decision_mutation()
        RETURNS trigger AS $$ BEGIN
            RAISE EXCEPTION 'Physical incident decisions are append-only';
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_physical_incident_decisions_immutable
        BEFORE UPDATE OR DELETE ON physical_incident_decisions
        FOR EACH ROW EXECUTE FUNCTION assetguard_prevent_physical_decision_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_physical_incident_decisions_immutable ON physical_incident_decisions")
    op.execute("DROP FUNCTION IF EXISTS assetguard_prevent_physical_decision_mutation()")
    op.drop_index("ix_physical_incident_decisions_incident_time", table_name="physical_incident_decisions")
    op.drop_table("physical_incident_decisions")
    op.drop_index("ix_physical_incidents_asset_time", table_name="physical_incidents")
    op.drop_index("ix_physical_incidents_room_status", table_name="physical_incidents")
    op.drop_table("physical_incidents")
