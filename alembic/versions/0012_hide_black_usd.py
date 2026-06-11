"""hide personal USD account (Black USD, low balance)

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-03
"""

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE accounts SET hidden = true"
            " WHERE currency = 'USD' AND is_fop = false"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE accounts SET hidden = false"
            " WHERE currency = 'USD' AND is_fop = false"
        )
    )
