"""Tests for pockets domain queries."""

import uuid

from sqlmodel import Session

from finance_api.domains.pockets import queries
from finance_api.domains.pockets.models import Pocket


def test_create_pocket_appears_in_list(session: Session) -> None:
    """A created pocket appears in list_pockets."""
    queries.create_pocket(
        session,
        category="Food",
        monthly_budget=3000.0,
        currency="UAH",
        emoji="🍔",
    )

    result = queries.list_pockets(session)
    assert len(result) == 1
    assert result[0]["category"] == "Food"
    assert abs(result[0]["monthly_budget"] - 3000.0) < 0.01
    assert abs(result[0]["balance"] - 3000.0) < 0.01
    assert result[0]["emoji"] == "🍔"


def test_drain_pocket_reduces_balance_and_floors_at_zero(session: Session) -> None:
    """drain_pocket reduces balance; a drain larger than the balance floors at 0."""
    pocket = queries.create_pocket(
        session,
        category="Transport",
        monthly_budget=1000.0,
        currency="UAH",
    )
    pocket_id = uuid.UUID(queries._to_dict(pocket)["id"])

    # Normal drain
    queries.drain_pocket(session, "Transport", 300.0, "UAH")
    session.expire_all()
    refreshed = session.get(Pocket, pocket_id)
    assert refreshed is not None
    assert abs(refreshed.balance - 700.0) < 0.01

    # Over-drain should floor at 0, not go negative
    queries.drain_pocket(session, "Transport", 9999.0, "UAH")
    session.expire_all()
    refreshed = session.get(Pocket, pocket_id)
    assert refreshed is not None
    assert refreshed.balance >= 0.0
    assert refreshed.balance < 0.01


def test_drain_pocket_no_matching_pocket_does_not_raise(session: Session) -> None:
    """drain_pocket with a category that has no pocket silently returns."""
    # Must not raise; there is no pocket for "Nonexistent"
    queries.drain_pocket(session, "Nonexistent", 100.0, "UAH")


def test_reset_all_pockets_restores_monthly_budget(session: Session) -> None:
    """reset_all_pockets resets every pocket's balance back to monthly_budget."""
    p1 = queries.create_pocket(session, category="Food", monthly_budget=3000.0)
    p2 = queries.create_pocket(session, category="Entertainment", monthly_budget=1500.0)

    # Drain both pockets so their balance differs from monthly_budget
    queries.drain_pocket(session, "Food", 1000.0, "UAH")
    queries.drain_pocket(session, "Entertainment", 500.0, "UAH")

    session.expire_all()
    p1_id = p1.id
    p2_id = p2.id
    assert session.get(Pocket, p1_id).balance < 3000.0  # type: ignore[union-attr]
    assert session.get(Pocket, p2_id).balance < 1500.0  # type: ignore[union-attr]

    count = queries.reset_all_pockets(session)
    assert count == 2

    session.expire_all()
    assert abs(session.get(Pocket, p1_id).balance - 3000.0) < 0.01  # type: ignore[union-attr]
    assert abs(session.get(Pocket, p2_id).balance - 1500.0) < 0.01  # type: ignore[union-attr]
