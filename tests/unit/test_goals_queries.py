"""Tests for goals domain queries."""

import uuid

from sqlmodel import Session

from finance_api.domains.goals import queries


def test_create_goal_appears_in_list(session: Session) -> None:
    """Created goal appears in the goals list with correct fields."""
    queries.create_goal(
        session,
        name="MacBook fund",
        target_amount=90000.0,
        currency="UAH",
        account_id=None,
        deadline=None,
        notes=None,
    )

    result = queries.list_goals(session)
    assert len(result) == 1
    assert result[0]["name"] == "MacBook fund"
    assert abs(result[0]["target_amount"] - 90000.0) < 0.01
    assert abs(result[0]["current_amount"]) < 0.01


def test_delete_goal_returns_false_on_repeat(session: Session) -> None:
    """Deleting the same goal twice — second call returns False."""
    created = queries.create_goal(
        session,
        name="Emergency fund",
        target_amount=50000.0,
        currency="UAH",
        account_id=None,
        deadline=None,
        notes=None,
    )
    goal_id = uuid.UUID(created["id"])

    first = queries.delete_goal(session, goal_id)
    second = queries.delete_goal(session, goal_id)

    assert first is True
    assert second is False


def test_goal_with_null_account_id_has_no_crash(session: Session) -> None:
    """Goal with account_id=None returns progress=0.0 without crashing."""
    queries.create_goal(
        session,
        name="Travel fund",
        target_amount=20000.0,
        currency="UAH",
        account_id=None,
        deadline=None,
        notes=None,
    )

    goals = queries.list_goals(session)
    assert len(goals) == 1
    assert goals[0]["account_id"] is None
    assert isinstance(goals[0]["progress"], float)
    assert abs(goals[0]["progress"]) < 0.0001
