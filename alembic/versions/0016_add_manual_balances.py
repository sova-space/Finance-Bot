"""add manual balances

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-18
"""

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = inspect(bind).get_table_names()
    if "manual_balances" in existing:
        return
    op.create_table(
        "manual_balances",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="UAH"),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column(
            "ownership_percent", sa.Float(), nullable=False, server_default="100.0"
        ),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_manual_balances_user_id", "manual_balances", ["user_id"])
    op.create_index("ix_manual_balances_kind", "manual_balances", ["kind"])


def downgrade() -> None:
    bind = op.get_bind()
    existing = inspect(bind).get_table_names()
    if "manual_balances" not in existing:
        return
    op.drop_index("ix_manual_balances_kind", table_name="manual_balances")
    op.drop_index("ix_manual_balances_user_id", table_name="manual_balances")
    op.drop_table("manual_balances")
