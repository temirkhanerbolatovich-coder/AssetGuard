"""Store auditable move and write-off operation details.

Revision ID: 0024_physical_asset_operations
Revises: 0023_physical_incident_workflow
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0024_physical_asset_operations"
down_revision = "0023_physical_incident_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("physical_incident_decisions", sa.Column("source_room_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("physical_incident_decisions", sa.Column("destination_room_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("physical_incident_decisions", sa.Column("destination_asset_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("physical_incident_decisions", sa.Column("quantity", sa.Integer(), nullable=True))
    op.add_column("physical_incident_decisions", sa.Column("document_number", sa.String(128), nullable=True))
    op.add_column("physical_incident_decisions", sa.Column("operation_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_foreign_key("fk_physical_decision_source_room", "physical_incident_decisions", "location_rooms", ["source_room_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_physical_decision_destination_room", "physical_incident_decisions", "location_rooms", ["destination_room_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_physical_decision_destination_asset", "physical_incident_decisions", "assets", ["destination_asset_id"], ["id"], ondelete="RESTRICT")
    op.create_check_constraint("ck_physical_decision_quantity", "physical_incident_decisions", "quantity IS NULL OR quantity > 0")


def downgrade() -> None:
    op.drop_constraint("ck_physical_decision_quantity", "physical_incident_decisions", type_="check")
    op.drop_constraint("fk_physical_decision_destination_asset", "physical_incident_decisions", type_="foreignkey")
    op.drop_constraint("fk_physical_decision_destination_room", "physical_incident_decisions", type_="foreignkey")
    op.drop_constraint("fk_physical_decision_source_room", "physical_incident_decisions", type_="foreignkey")
    for column in ("operation_snapshot", "document_number", "quantity", "destination_asset_id", "destination_room_id", "source_room_id"):
        op.drop_column("physical_incident_decisions", column)
