"""Test that get_spending_by_category returns separate rows per currency (Bug #1)."""

import uuid
from datetime import date

from sqlmodel import Session

from finance_api.domains.accounts.models import Account
from finance_api.domains.insights.queries import get_spending_by_category
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions.models import Transaction


def _make_account(session: Session) -> uuid.UUID:
    account = Account(
        monobank_id="test_account",
        name="Test Account",
        currency="UAH",
        account_type="black",
        balance=0.0,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account.id


def test_same_category_different_currencies_are_separate_rows(
    session: Session,
) -> None:
    """Two transactions in the same category but different currencies must not be
    summed together — they must appear as separate rows."""
    account_id = _make_account(session)
    today = date.today()

    session.add(
        Transaction(
            account_id=account_id,
            monobank_id="tx_uah_1",
            amount=-500.0,
            currency="UAH",
            date=today,
            description="Supermarket",
            category=cat.GROCERIES,
        )
    )
    session.add(
        Transaction(
            account_id=account_id,
            monobank_id="tx_usd_1",
            amount=-20.0,
            currency="USD",
            date=today,
            description="Supermarket US",
            category=cat.GROCERIES,
        )
    )
    session.commit()

    rows = get_spending_by_category(period="this_month")

    groceries_rows = [r for r in rows if r["category"] == cat.GROCERIES]
    assert len(groceries_rows) == 2, (
        f"Expected 2 rows (one per currency), "
        f"got {len(groceries_rows)}: {groceries_rows}"
    )

    currencies = {r["currency"] for r in groceries_rows}
    assert currencies == {"UAH", "USD"}

    uah_row = next(r for r in groceries_rows if r["currency"] == "UAH")
    usd_row = next(r for r in groceries_rows if r["currency"] == "USD")
    assert abs(uah_row["amount"] - 500.0) < 0.01
    assert abs(usd_row["amount"] - 20.0) < 0.01


def test_same_category_same_currency_is_aggregated(session: Session) -> None:
    """Two UAH transactions in the same category are still summed into one row."""
    account_id = _make_account(session)
    today = date.today()

    session.add(
        Transaction(
            account_id=account_id,
            monobank_id="tx_uah_2",
            amount=-300.0,
            currency="UAH",
            date=today,
            description="Cafe 1",
            category=cat.FOOD_AND_DRINK,
        )
    )
    session.add(
        Transaction(
            account_id=account_id,
            monobank_id="tx_uah_3",
            amount=-200.0,
            currency="UAH",
            date=today,
            description="Cafe 2",
            category=cat.FOOD_AND_DRINK,
        )
    )
    session.commit()

    rows = get_spending_by_category(period="this_month")

    food_rows = [r for r in rows if r["category"] == cat.FOOD_AND_DRINK]
    assert len(food_rows) == 1
    assert food_rows[0]["currency"] == "UAH"
    assert abs(food_rows[0]["amount"] - 500.0) < 0.01


def test_row_schema_has_required_keys(session: Session) -> None:
    """Each row must have exactly the keys: category, currency, amount."""
    account_id = _make_account(session)
    today = date.today()

    session.add(
        Transaction(
            account_id=account_id,
            monobank_id="tx_schema_check",
            amount=-100.0,
            currency="UAH",
            date=today,
            description="Test",
            category=cat.SHOPPING,
        )
    )
    session.commit()

    rows = get_spending_by_category(period="this_month")
    assert rows, "Expected at least one row"
    for row in rows:
        assert set(row.keys()) == {"category", "currency", "amount"}, (
            f"Unexpected keys in row: {set(row.keys())}"
        )
