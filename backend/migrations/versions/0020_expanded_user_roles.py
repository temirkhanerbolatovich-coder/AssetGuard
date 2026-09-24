"""Allow location-scoped staff roles for named users.

Revision ID: 0020_expanded_user_roles
Revises: 0019_location_access
"""
from alembic import op

revision = "0020_expanded_user_roles"
down_revision = "0019_location_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('ADMIN', 'VIEWER', 'LOCATION_MANAGER', 'INVENTORY_CLERK')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('ADMIN', 'VIEWER')",
    )
