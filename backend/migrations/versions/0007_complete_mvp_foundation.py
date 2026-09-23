"""Complete the MVP event, asset history, and endpoint linkage foundation.

Revision ID: 0007_complete_mvp_foundation
Revises: 0006_assets
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_complete_mvp_foundation"
down_revision = "0006_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_managed_endpoints_one_per_asset", "managed_endpoints", ["asset_id"],
        unique=True, postgresql_where=sa.text("asset_id IS NOT NULL"),
    )
    op.drop_constraint("ck_change_events_component_type", "change_events", type_="check")
    op.drop_constraint("ck_change_events_type", "change_events", type_="check")
    op.create_check_constraint(
        "ck_change_events_component_type", "change_events",
        "component_type IN ('RAM', 'STORAGE', 'ENDPOINT')",
    )
    op.create_check_constraint(
        "ck_change_events_type", "change_events",
        "event_type IN ('COMPONENT_ADDED', 'COMPONENT_REMOVED', "
        "'COMPONENT_CHANGED', 'COMPONENT_REPLACED', "
        "'DEVICE_IDENTITY_CHANGED', 'HOSTNAME_CHANGED')",
    )
    op.create_table(
        "asset_history_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("managed_endpoint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("related_entity_type", sa.String(64), nullable=False),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["managed_endpoint_id"], ["managed_endpoints.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_asset_history_entries"),
    )
    op.create_index("ix_asset_history_asset_time", "asset_history_entries", ["asset_id", "occurred_at"])
    op.execute(
        """
        CREATE FUNCTION assetguard_prevent_asset_history_mutation()
        RETURNS trigger AS $$ BEGIN
            RAISE EXCEPTION 'Asset history entries are append-only';
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_asset_history_immutable
        BEFORE UPDATE OR DELETE ON asset_history_entries
        FOR EACH ROW EXECUTE FUNCTION assetguard_prevent_asset_history_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_asset_history_immutable ON asset_history_entries")
    op.execute("DROP FUNCTION IF EXISTS assetguard_prevent_asset_history_mutation()")
    op.drop_index("ix_asset_history_asset_time", table_name="asset_history_entries")
    op.drop_table("asset_history_entries")
    op.drop_constraint("ck_change_events_type", "change_events", type_="check")
    op.drop_constraint("ck_change_events_component_type", "change_events", type_="check")
    op.create_check_constraint("ck_change_events_component_type", "change_events", "component_type IN ('RAM', 'STORAGE')")
    op.create_check_constraint("ck_change_events_type", "change_events", "event_type IN ('COMPONENT_ADDED', 'COMPONENT_REMOVED')")
    op.drop_index("uq_managed_endpoints_one_per_asset", table_name="managed_endpoints")
