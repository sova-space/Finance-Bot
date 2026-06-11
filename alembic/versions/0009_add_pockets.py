"""add pockets and pocket_transfers tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-31
"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pockets",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("category", sa.Text(), nullable=False, unique=True),
        sa.Column("monthly_budget", sa.Float(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False, server_default="UAH"),
        sa.Column("balance", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("emoji", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "pocket_transfers",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "from_pocket_id",
            sa.Uuid(),
            sa.ForeignKey("pockets.id"),
            nullable=True,
        ),
        sa.Column(
            "to_pocket_id",
            sa.Uuid(),
            sa.ForeignKey("pockets.id"),
            nullable=True,
        ),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False, server_default="UAH"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("pocket_transfers")
    op.drop_table("pockets")
