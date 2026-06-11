"""Tests for trips domain queries."""

import uuid
from datetime import date

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from finance_api.domains.trips import queries
from finance_api.routers.trips import TripCreate


def test_create_trip_with_invalid_dates_raises_422() -> None:
    """TripCreate validator raises ValidationError when end_date < start_date."""
    with pytest.raises(ValidationError):
        TripCreate(
            name="Bad trip",
            start_date=date(2026, 6, 10),
            end_date=date(2026, 6, 1),
        )


def test_get_trip_spending_on_nonexistent_trip_returns_none(session: Session) -> None:
    """Fetching a non-existent trip returns None from get_trip query."""
    trip = queries.get_trip(session, uuid.uuid4())
    assert trip is None


def test_trip_spending_scoped_to_date_range(session: Session, monkeypatch) -> None:
    """Trip spending uses the trip's date range, not a named period."""
    from datetime import date

    # Use the session's engine for the spending query
    import finance_api.domains.insights.queries as q_module
    from finance_api.domains.accounts.models import Account
    from finance_api.domains.transactions.models import Transaction

    test_engine = session.get_bind()
    monkeypatch.setattr(q_module, "engine", test_engine)

    account = Account(
        monobank_id="trip_acct",
        name="Trip Account",
        currency="UAH",
        account_type="black",
        balance=0.0,
    )
    session.add(account)
    session.commit()
    session.refresh(account)

    # Transaction inside trip range
    session.add(
        Transaction(
            account_id=account.id,
            monobank_id="tx_in_trip",
            amount=-300.0,
            currency="UAH",
            date=date(2026, 6, 3),
            description="Hotel",
            category="Travel",
        )
    )
    # Transaction outside trip range
    session.add(
        Transaction(
            account_id=account.id,
            monobank_id="tx_outside_trip",
            amount=-1000.0,
            currency="UAH",
            date=date(2026, 5, 15),
            description="Grocery",
            category="Groceries",
        )
    )
    session.commit()

    created = queries.create_trip(
        session,
        name="Warsaw June",
        budget=15000.0,
        currency="UAH",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 7),
        notes=None,
    )
    trip_id = uuid.UUID(created["id"])
    trip = queries.get_trip(session, trip_id)

    from finance_api.domains.insights.queries import get_spending_by_category

    spending = get_spending_by_category(start=trip.start_date, end=trip.end_date)

    categories = [r["category"] for r in spending]
    assert "Travel" in categories
    assert "Groceries" not in categories
