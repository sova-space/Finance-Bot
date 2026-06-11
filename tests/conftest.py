"""Shared fixtures for finance_api tests."""

import os
from collections.abc import Generator

import pytest
from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Session, SQLModel, create_engine

# Must be set before any finance_api imports so Settings() does not fail.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("MONOBANK_TOKEN", "test_token")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TELEGRAM_OWNER_ID", "12345")

from finance_api.domains.accounts.models import Account  # noqa: F401
from finance_api.domains.buy_list.models import BuyListItem  # noqa: F401
from finance_api.domains.debt.models import Debt  # noqa: F401
from finance_api.domains.forecast.models import (  # noqa: F401
    ExpectedIncomeItem,
    RecurringItem,
)
from finance_api.domains.goals.models import Goal  # noqa: F401
from finance_api.domains.pockets.models import Pocket, PocketTransfer  # noqa: F401
from finance_api.domains.rules.models import TransactionRule  # noqa: F401
from finance_api.domains.transactions.models import Transaction
from finance_api.domains.trips.models import Trip  # noqa: F401


def _make_test_engine():
    """Create a SQLite in-memory engine with foreign-key enforcement.

    PostgreSQL-specific JSONB columns are remapped to plain JSON so that
    ``SQLModel.metadata.create_all`` succeeds on SQLite.
    """
    # Remap JSONB → JSON in the Transaction.extra column for SQLite compatibility
    extra_col = Transaction.__table__.c.get("extra")
    if extra_col is not None and isinstance(extra_col.type, JSONB):
        extra_col.type = JSON()

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(test_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(test_engine)
    return test_engine


@pytest.fixture()
def session(monkeypatch) -> Generator[Session, None, None]:
    """SQLite in-memory Session with schema pre-created.

    Patches the module-level ``engine`` in every query module so that
    production code runs against the test database without modification.
    """
    import finance_api.domains.budgets.queries as b_module
    import finance_api.domains.insights.queries as q_module
    import finance_api.domains.sync.monobank as sync_module

    test_engine = _make_test_engine()

    monkeypatch.setattr(q_module, "engine", test_engine)
    monkeypatch.setattr(b_module, "engine", test_engine)
    monkeypatch.setattr(sync_module, "engine", test_engine)

    with Session(test_engine) as s:
        yield s
