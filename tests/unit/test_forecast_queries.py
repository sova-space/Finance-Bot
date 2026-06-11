"""Tests for forecast domain queries."""

import uuid

from sqlmodel import Session

from finance_api.domains.forecast import queries


def test_forecast_with_no_data_returns_zero_projections(
    session: Session, monkeypatch
) -> None:
    """GET /forecast with empty DB returns zero projections without error."""
    import finance_api.domains.insights.queries as q_module

    test_engine = session.get_bind()
    monkeypatch.setattr(q_module, "engine", test_engine)

    result = queries.get_forecast(session)

    assert "balances" in result
    assert "recurring" in result
    assert "income" in result
    assert "projected_variable_spend" in result
    assert "forecast_by_currency" in result
    assert result["recurring"] == []
    assert result["income"] == []
    assert result["projected_variable_spend"] == []


def test_create_recurring_item_appears_in_list(session: Session) -> None:
    """Created recurring item appears in the recurring list."""
    queries.create_recurring(
        session,
        name="Netflix",
        amount=199.0,
        currency="UAH",
        day_of_month=15,
        category=None,
    )

    result = queries.list_recurring(session)
    assert len(result) == 1
    assert result[0]["name"] == "Netflix"
    assert abs(result[0]["amount"] - 199.0) < 0.01
    assert result[0]["active"] is True


def test_deactivated_recurring_excluded_from_forecast(
    session: Session, monkeypatch
) -> None:
    """Deactivated recurring item is not included in forecast calculation."""
    import finance_api.domains.insights.queries as q_module

    test_engine = session.get_bind()
    monkeypatch.setattr(q_module, "engine", test_engine)

    created = queries.create_recurring(
        session,
        name="Gym membership",
        amount=500.0,
        currency="UAH",
        day_of_month=1,
        category=None,
    )
    item_id = uuid.UUID(created["id"])

    # Deactivate it
    queries.update_recurring(session, item_id, {"active": False})

    result = queries.get_forecast(session)
    active_ids = [r["id"] for r in result["recurring"]]
    assert str(item_id) not in active_ids
