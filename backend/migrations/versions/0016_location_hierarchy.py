"""Add managed building, floor and room hierarchy.

Revision ID: 0016_location_hierarchy
Revises: 0015_vision_tenant_scope
"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016_location_hierarchy"
down_revision = "0015_vision_tenant_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("location_buildings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False), sa.Column("responsible_name", sa.String(255)), sa.Column("responsible_contact", sa.String(255)), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("organization_id", "name", name="uq_location_building_org_name"),
    )
    op.create_table("location_floors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("building_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("name", sa.String(64), nullable=False), sa.Column("responsible_name", sa.String(255)), sa.Column("responsible_contact", sa.String(255)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["building_id"], ["location_buildings.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("building_id", "name", name="uq_location_floor_building_name"),
    )
    op.create_table("location_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("floor_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("purpose", sa.String(255)), sa.Column("responsible_name", sa.String(255)), sa.Column("responsible_contact", sa.String(255)), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["floor_id"], ["location_floors.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("floor_id", "name", name="uq_location_room_floor_name"),
    )
    op.add_column("assets", sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_assets_location_room", "assets", "location_rooms", ["room_id"], ["id"], ondelete="RESTRICT")
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, organization_id, building, floor, room, created_at FROM assets WHERE building IS NOT NULL OR floor IS NOT NULL OR room IS NOT NULL")).mappings()
    for asset in rows:
        building_name = asset["building"] or "Не указан корпус"
        floor_name = asset["floor"] or "Не указан этаж"
        building_id = bind.execute(sa.text("SELECT id FROM location_buildings WHERE organization_id=:organization_id AND name=:name"), {"organization_id": asset["organization_id"], "name": building_name}).scalar()
        if not building_id:
            building_id = uuid4(); bind.execute(sa.text("INSERT INTO location_buildings (id, organization_id, name, created_at) VALUES (:id, :organization_id, :name, :created_at)"), {"id": building_id, "organization_id": asset["organization_id"], "name": building_name, "created_at": asset["created_at"]})
        floor_id = bind.execute(sa.text("SELECT id FROM location_floors WHERE building_id=:building_id AND name=:name"), {"building_id": building_id, "name": floor_name}).scalar()
        if not floor_id:
            floor_id = uuid4(); bind.execute(sa.text("INSERT INTO location_floors (id, building_id, name, created_at) VALUES (:id, :building_id, :name, :created_at)"), {"id": floor_id, "building_id": building_id, "name": floor_name, "created_at": asset["created_at"]})
        if asset["room"]:
            room_id = bind.execute(sa.text("SELECT id FROM location_rooms WHERE floor_id=:floor_id AND name=:name"), {"floor_id": floor_id, "name": asset["room"]}).scalar()
            if not room_id:
                room_id = uuid4(); bind.execute(sa.text("INSERT INTO location_rooms (id, floor_id, name, created_at) VALUES (:id, :floor_id, :name, :created_at)"), {"id": room_id, "floor_id": floor_id, "name": asset["room"], "created_at": asset["created_at"]})
            bind.execute(sa.text("UPDATE assets SET room_id=:room_id WHERE id=:id"), {"room_id": room_id, "id": asset["id"]})


def downgrade() -> None:
    op.drop_constraint("fk_assets_location_room", "assets", type_="foreignkey")
    op.drop_column("assets", "room_id")
    op.drop_table("location_rooms")
    op.drop_table("location_floors")
    op.drop_table("location_buildings")
