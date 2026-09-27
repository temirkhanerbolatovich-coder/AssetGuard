"""Add administrator-approved Agent re-enrolment.

Revision ID: 0025_agent_reenrolment
Revises: 0024_physical_asset_operations
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0025_agent_reenrolment"
down_revision = "0024_physical_asset_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_agent_credentials_endpoint", "agent_credentials", type_="unique")
    op.create_index(
        "uq_agent_credentials_active_endpoint",
        "agent_credentials",
        ["managed_endpoint_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND managed_endpoint_id IS NOT NULL"),
    )
    op.create_table(
        "agent_reenrolments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("credential_secret_hash", sa.Text(), nullable=False),
        sa.Column("identifier_type", sa.String(32), nullable=False),
        sa.Column("identifier_value", sa.String(512), nullable=False),
        sa.Column("computer_name", sa.String(255), nullable=False),
        sa.Column("installer_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("managed_endpoint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.String(255), nullable=True),
        sa.CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED')", name="ck_agent_reenrolments_status"),
        sa.ForeignKeyConstraint(["managed_endpoint_id"], ["managed_endpoints.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["credential_id"], ["agent_credentials.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_reenrolments"),
        sa.UniqueConstraint("token_hash", name="uq_agent_reenrolments_token_hash"),
    )
    op.create_index("ix_agent_reenrolments_status_expires", "agent_reenrolments", ["status", "expires_at"])
    op.create_index("ix_agent_reenrolments_organization", "agent_reenrolments", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_reenrolments_organization", table_name="agent_reenrolments")
    op.drop_index("ix_agent_reenrolments_status_expires", table_name="agent_reenrolments")
    op.drop_table("agent_reenrolments")
    op.drop_index("uq_agent_credentials_active_endpoint", table_name="agent_credentials")
    # The previous schema allowed only one credential row per endpoint. Re-enrolment
    # deliberately preserves revoked credentials for audit, so detach those historical
    # rows before restoring the old uniqueness constraint during an explicit downgrade.
    op.execute(
        "UPDATE agent_credentials "
        "SET managed_endpoint_id = NULL "
        "WHERE status = 'REVOKED' AND managed_endpoint_id IS NOT NULL"
    )
    op.create_unique_constraint("uq_agent_credentials_endpoint", "agent_credentials", ["managed_endpoint_id"])
