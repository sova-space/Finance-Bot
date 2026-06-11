"""add transaction_rules table with seed data

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-03
"""

import uuid
from datetime import datetime

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

SEED_RULES = [
    ("partner_transfer", "Олена", "Partner"),
    ("partner_transfer", "Olena", "Partner"),
    ("partner_transfer", "olena", "Partner"),
    ("personal_income", "Олександра Хімін", "Unanet"),
    ("passthrough", "СТАБІЛЬ ГЛОБАЛ", "СТАБІЛЬ ГЛОБАЛ"),
]


def upgrade() -> None:
    op.create_table(
        "transaction_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_type", sa.String(), nullable=False),
        sa.Column("pattern", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    now = datetime.utcnow()
    op.bulk_insert(
        sa.table(
            "transaction_rules",
            sa.column("id", sa.Uuid()),
            sa.column("rule_type", sa.String()),
            sa.column("pattern", sa.String()),
            sa.column("label", sa.String()),
            sa.column("created_at", sa.DateTime()),
        ),
        [
            {
                "id": uuid.uuid4(),
                "rule_type": rule_type,
                "pattern": pattern,
                "label": label,
                "created_at": now,
            }
            for rule_type, pattern, label in SEED_RULES
        ],
    )


def downgrade() -> None:
    op.drop_table("transaction_rules")
