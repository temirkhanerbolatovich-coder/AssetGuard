"""Add immutable physical room inspection acts.

Revision ID: 0022_room_physical_inspections
Revises: 0021_vision_location_scope
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0022_room_physical_inspections"
down_revision = "0021_vision_location_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "room_inspections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspector_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("inspector_name", sa.String(255), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["location_rooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inspector_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_room_inspections"),
    )
    op.create_index("ix_room_inspections_room_time", "room_inspections", ["room_id", "completed_at"])
    op.create_table(
        "room_inspection_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("expected_quantity", sa.Integer(), nullable=False),
        sa.Column("affected_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.CheckConstraint("result IN ('PRESENT', 'MISSING', 'DAMAGED')", name="ck_room_inspection_item_result"),
        sa.CheckConstraint("expected_quantity >= 1", name="ck_room_inspection_expected_quantity"),
        sa.CheckConstraint("affected_quantity >= 0 AND affected_quantity <= expected_quantity", name="ck_room_inspection_affected_quantity"),
        sa.ForeignKeyConstraint(["inspection_id"], ["room_inspections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_room_inspection_items"),
        sa.UniqueConstraint("inspection_id", "asset_id", name="uq_room_inspection_asset"),
    )
    op.create_index("ix_room_inspection_items_inspection", "room_inspection_items", ["inspection_id"])
    op.execute(
        """
        CREATE FUNCTION assetguard_prevent_room_inspection_mutation()
        RETURNS trigger AS $$ BEGIN
            RAISE EXCEPTION 'Room inspection acts are append-only';
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_room_inspections_immutable
        BEFORE UPDATE OR DELETE ON room_inspections
        FOR EACH ROW EXECUTE FUNCTION assetguard_prevent_room_inspection_mutation();
        CREATE TRIGGER trg_room_inspection_items_immutable
        BEFORE UPDATE OR DELETE ON room_inspection_items
        FOR EACH ROW EXECUTE FUNCTION assetguard_prevent_room_inspection_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_room_inspection_items_immutable ON room_inspection_items")
    op.execute("DROP TRIGGER IF EXISTS trg_room_inspections_immutable ON room_inspections")
    op.execute("DROP FUNCTION IF EXISTS assetguard_prevent_room_inspection_mutation()")
    op.drop_index("ix_room_inspection_items_inspection", table_name="room_inspection_items")
    op.drop_table("room_inspection_items")
    op.drop_index("ix_room_inspections_room_time", table_name="room_inspections")
    op.drop_table("room_inspections")
