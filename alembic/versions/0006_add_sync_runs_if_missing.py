"""add sync_runs if missing (0001 skipped it for pre-alembic databases)

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-29
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    tables = sa.inspect(conn).get_table_names()
    if "sync_runs" in tables:
        return
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("tx_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("sync_runs")
