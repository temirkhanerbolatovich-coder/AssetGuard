"""Classify grouped accounting-statement imports.

Revision ID: 0018_classify_imported_property
Revises: 0017_asset_accounting_modes
"""
from alembic import op

revision = "0018_classify_imported_property"
down_revision = "0017_asset_accounting_modes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These rows came from a single accounting statement: each row is a quantity,
    # not yet a device that can be attached to an Agent.
    op.execute("""
        UPDATE assets
        SET tracking_mode = 'GROUPED',
            quantity = COALESCE(NULLIF(substring(notes FROM 'Количество по ведомости: ([0-9]+)'), '')::integer, 1),
            category = CASE
                WHEN lower(name) ~ '(компьютер|ноутбук|принтер|мфу|проектор|монитор|планшет)' THEN 'IT'
                WHEN lower(name) ~ '(мяч|мат |форма |ракет|теннис|спорт|тренаж)' THEN 'SPORTS'
                WHEN lower(name) ~ '(стол|стул|шкаф|кабинет)' THEN 'FURNITURE'
                WHEN lower(name) ~ '(доска|лаборатор|интерактив)' THEN 'EDUCATIONAL'
                ELSE 'OTHER'
            END
        WHERE inventory_number LIKE 'PDF-3333-%'
    """)


def downgrade() -> None:
    op.execute("UPDATE assets SET category = 'IT', tracking_mode = 'INDIVIDUAL', quantity = 1 WHERE inventory_number LIKE 'PDF-3333-%'")
