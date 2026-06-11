"""Tests for debt domain queries."""

import uuid
from datetime import UTC

from sqlmodel import Session

from finance_api.domains.debt import queries


def test_create_debt_and_list(session: Session) -> None:
    """Created debt appears in the default open list."""
    queries.create_debt(
        session,
        person="Іванко",
        amount=500.0,
        currency="UAH",
        description="lunch",
        due_date=None,
    )

    result = queries.list_debts(session, settled="false")
    assert len(result) == 1
    assert result[0]["person"] == "Іванко"
    assert abs(result[0]["amount"] - 500.0) < 0.01
    assert result[0]["settled_at"] is None


def test_settled_debt_absent_from_open_list(session: Session) -> None:
    """Settling a debt removes it from the open list and adds it to settled."""
    created = queries.create_debt(
        session,
        person="Олена",
        amount=200.0,
        currency="UAH",
        description=None,
        due_date=None,
    )
    debt_id = uuid.UUID(created["id"])

    from datetime import datetime

    queries.update_debt(
        session,
        debt_id,
        {"settled_at": datetime.now(UTC).replace(tzinfo=None)},
    )

    open_debts = queries.list_debts(session, settled="false")
    settled_debts = queries.list_debts(session, settled="true")
    all_debts = queries.list_debts(session, settled="all")

    assert not any(d["id"] == str(debt_id) for d in open_debts)
    assert any(d["id"] == str(debt_id) for d in settled_debts)
    assert any(d["id"] == str(debt_id) for d in all_debts)


def test_delete_nonexistent_debt_returns_false(session: Session) -> None:
    """Deleting a non-existent debt ID returns False (router maps to 404)."""
    result = queries.delete_debt(session, uuid.uuid4())
    assert result is False
