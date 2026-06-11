"""add hidden flag to accounts

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-03
"""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.add_column(
            sa.Column("hidden", sa.Boolean(), nullable=False, server_default="false")
        )


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("hidden")
