"""mark FOP UAH and EUR accounts as hidden

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-03
"""

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE accounts SET hidden = true"
            " WHERE (is_fop = true AND currency = 'UAH')"
            "    OR currency = 'EUR'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE accounts SET hidden = false"
            " WHERE (is_fop = true AND currency = 'UAH')"
            "    OR currency = 'EUR'"
        )
    )
