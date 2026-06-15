"""add hosted multi-user foundation

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-14
"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def _has_column(conn: sa.engine.Connection, table: str, column: str) -> bool:
    return column in {c["name"] for c in sa.inspect(conn).get_columns(table)}


def _constraint_names(conn: sa.engine.Connection, table: str) -> set[str]:
    inspector = sa.inspect(conn)
    names = {
        c["name"] for c in inspector.get_unique_constraints(table) if c.get("name")
    }
    names.update({i["name"] for i in inspector.get_indexes(table) if i.get("unique")})
    return names


def _drop_unique_if_exists(table: str, names: list[str]) -> None:
    conn = op.get_bind()
    existing = _constraint_names(conn, table)
    for name in names:
        if name in existing:
            op.drop_constraint(name, table, type_="unique")


def upgrade() -> None:
    conn = op.get_bind()
    tables = set(sa.inspect(conn).get_table_names())

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
            sa.Column("encrypted_monobank_token", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),
        )
        op.create_index("ix_users_telegram_user_id", "users", ["telegram_user_id"])

    if not _has_column(conn, "accounts", "user_id"):
        op.add_column("accounts", sa.Column("user_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "fk_accounts_user_id", "accounts", "users", ["user_id"], ["id"]
        )
        op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    if not _has_column(conn, "transactions", "user_id"):
        op.add_column("transactions", sa.Column("user_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "fk_transactions_user_id", "transactions", "users", ["user_id"], ["id"]
        )
        op.create_index("ix_transactions_user_id", "transactions", ["user_id"])

    _drop_unique_if_exists("accounts", ["accounts_monobank_id_key"])
    _drop_unique_if_exists("transactions", ["transactions_monobank_id_key"])

    existing_indexes = {i["name"] for i in sa.inspect(conn).get_indexes("accounts")}
    if "uq_accounts_user_monobank" not in existing_indexes:
        op.create_index(
            "uq_accounts_user_monobank",
            "accounts",
            ["user_id", "monobank_id"],
            unique=True,
        )
    existing_tx_indexes = {
        i["name"] for i in sa.inspect(conn).get_indexes("transactions")
    }
    if "uq_transactions_user_monobank" not in existing_tx_indexes:
        op.create_index(
            "uq_transactions_user_monobank",
            "transactions",
            ["user_id", "monobank_id"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("uq_transactions_user_monobank", table_name="transactions")
    op.drop_index("uq_accounts_user_monobank", table_name="accounts")
    op.drop_index("ix_transactions_user_id", table_name="transactions")
    op.drop_constraint("fk_transactions_user_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "user_id")
    op.drop_index("ix_accounts_user_id", table_name="accounts")
    op.drop_constraint("fk_accounts_user_id", "accounts", type_="foreignkey")
    op.drop_column("accounts", "user_id")
    op.drop_index("ix_users_telegram_user_id", table_name="users")
    op.drop_table("users")
