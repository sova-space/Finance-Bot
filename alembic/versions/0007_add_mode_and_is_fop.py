"""add mode to transactions and is_fop to accounts

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-31
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_PARTNER_PATTERNS = ["Олена", "Olena", "olena"]


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("mode", sa.Text(), nullable=True))

    with op.batch_alter_table("accounts") as batch_op:
        batch_op.add_column(
            sa.Column("is_fop", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    conn = op.get_bind()

    # Backfill is_fop from account_type
    conn.execute(
        sa.text("UPDATE accounts SET is_fop = TRUE WHERE account_type = 'fop'")
    )

    # Backfill mode: partner transfers → couple
    for pattern in _PARTNER_PATTERNS:
        conn.execute(
            sa.text(
                "UPDATE transactions SET mode = 'couple', category = 'Couple Transfer'"
                " WHERE amount < 0 AND description ILIKE :pattern AND mode IS NULL"
            ),
            {"pattern": f"%{pattern}%"},
        )

    # Backfill mode: all remaining negative transactions → solo
    conn.execute(
        sa.text(
            "UPDATE transactions SET mode = 'solo' WHERE amount < 0 AND mode IS NULL"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_column("mode")

    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("is_fop")
