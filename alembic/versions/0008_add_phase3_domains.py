"""add phase 3 domain tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-31
"""

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = inspect(bind).get_table_names()

    if "debts" not in existing:
        op.create_table(
            "debts",
            sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
            sa.Column("person", sa.Text(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.Text(), nullable=False, server_default="UAH"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("settled_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if "goals" not in existing:
        op.create_table(
            "goals",
            sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("target_amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.Text(), nullable=False, server_default="UAH"),
            sa.Column(
                "current_amount", sa.Float(), nullable=False, server_default="0.0"
            ),
            sa.Column("account_id", sa.Uuid(), nullable=True),
            sa.Column("deadline", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("achieved_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if "trips" not in existing:
        op.create_table(
            "trips",
            sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("budget", sa.Float(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=False, server_default="UAH"),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if "buy_list_items" not in existing:
        op.create_table(
            "buy_list_items",
            sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("target_price", sa.Float(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=True),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("bought_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if "recurring_items" not in existing:
        op.create_table(
            "recurring_items",
            sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.Text(), nullable=False, server_default="UAH"),
            sa.Column("day_of_month", sa.Integer(), nullable=True),
            sa.Column("category", sa.Text(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if "expected_income_items" not in existing:
        op.create_table(
            "expected_income_items",
            sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.Text(), nullable=False, server_default="UAH"),
            sa.Column("day_of_month", sa.Integer(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )


def downgrade() -> None:
    op.drop_table("expected_income_items")
    op.drop_table("recurring_items")
    op.drop_table("buy_list_items")
    op.drop_table("trips")
    op.drop_table("goals")
    op.drop_table("debts")
