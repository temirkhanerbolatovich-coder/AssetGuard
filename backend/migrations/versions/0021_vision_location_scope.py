"""Link Vision rooms to canonical school locations for access checks.

Revision ID: 0021_vision_location_scope
Revises: 0020_expanded_user_roles
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0021_vision_location_scope"
down_revision = "0020_expanded_user_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vision_rooms",
        sa.Column("location_room_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_vision_rooms_location_room", "vision_rooms", "location_rooms",
        ["location_room_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_vision_rooms_location_room", "vision_rooms", ["location_room_id"],
    )
    # Backfill only exact, unambiguous matches inside the same organization.
    # Ambiguous legacy rooms remain unlinked and hidden from scoped non-admin users.
    op.execute("""
        UPDATE vision_rooms AS vr
        SET location_room_id = candidates.room_id
        FROM (
            SELECT vr2.id AS vision_room_id, MIN(r.id::text)::uuid AS room_id
            FROM vision_rooms AS vr2
            JOIN location_rooms AS r ON r.name = vr2.name
            JOIN location_floors AS f ON f.id = r.floor_id
            JOIN location_buildings AS b ON b.id = f.building_id
            WHERE vr2.organization_id = b.organization_id
            GROUP BY vr2.id
            HAVING COUNT(r.id) = 1
        ) AS candidates
        WHERE vr.id = candidates.vision_room_id
    """)


def downgrade() -> None:
    op.drop_constraint("uq_vision_rooms_location_room", "vision_rooms", type_="unique")
    op.drop_constraint("fk_vision_rooms_location_room", "vision_rooms", type_="foreignkey")
    op.drop_column("vision_rooms", "location_room_id")
