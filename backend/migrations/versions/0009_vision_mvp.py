"""Add the minimal room-level Vision scan workflow.

Revision ID: 0009_vision_mvp
Revises: 0008_users_and_sessions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_vision_mvp"
down_revision = "0008_users_and_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vision_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_vision_rooms"),
        sa.UniqueConstraint("name", name="uq_vision_rooms_name"),
    )
    op.create_table(
        "vision_scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("original_image_path", sa.Text(), nullable=False),
        sa.Column("annotated_image_path", sa.Text(), nullable=False),
        sa.Column("counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("comparison", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("confidence_threshold", sa.Float(), nullable=False),
        sa.CheckConstraint("status IN ('NOT_CHECKED', 'OK', 'WARNING')", name="ck_vision_scans_status"),
        sa.ForeignKeyConstraint(["room_id"], ["vision_rooms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_vision_scans"),
    )
    op.create_index("ix_vision_scans_room_time", "vision_scans", ["room_id", "created_at"])
    op.create_table(
        "vision_detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_name", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["vision_scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_vision_detections"),
    )
    op.create_index("ix_vision_detections_scan", "vision_detections", ["scan_id"])
    op.create_table(
        "vision_baselines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["vision_rooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_scan_id"], ["vision_scans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_vision_baselines"),
        sa.UniqueConstraint("room_id", name="uq_vision_baselines_room"),
    )


def downgrade() -> None:
    op.drop_table("vision_baselines")
    op.drop_index("ix_vision_detections_scan", table_name="vision_detections")
    op.drop_table("vision_detections")
    op.drop_index("ix_vision_scans_room_time", table_name="vision_scans")
    op.drop_table("vision_scans")
    op.drop_table("vision_rooms")
