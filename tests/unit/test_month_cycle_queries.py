"""Calendar month query tests."""

from datetime import date, timedelta

import pytest

from finance_api.domains.accounts.models import Account
from finance_api.domains.insights import queries
from finance_api.domains.rules.models import TransactionRule
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions.models import Transaction


def _account(session, *, is_fop=False, balance=0, currency="UAH"):
    account = Account(
        monobank_id=f"acc-{is_fop}-{balance}-{currency}",
        name="Card",
        currency=currency,
        account_type="black",
        is_fop=is_fop,
        balance=balance,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def test_current_month_uses_calendar_month_from_first_day(session):
    account = _account(session)
    today = date.today()
    current_start = today.replace(day=1)
    previous_month_day = current_start - timedelta(days=1)
    session.add_all([
        Transaction(
            account_id=account.id,
            monobank_id="old-food",
            amount=-900,
            currency="UAH",
            date=previous_month_day,
            description="Old food",
            category=cat.FOOD_AND_DRINK,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="new-food",
            amount=-300,
            currency="UAH",
            date=current_start,
            description="New food",
            category=cat.FOOD_AND_DRINK,
        ),
    ])
    session.commit()

    summary = queries.get_month_cycle_summary(offset=0)

    assert summary["spending"]["period_start"] == current_start.isoformat()
    assert summary["has_previous"] is True
    assert summary["has_next"] is False
    assert summary["spending"]["rows"] == [
        {"category": cat.FOOD_AND_DRINK, "currency": "UAH", "amount": 300.0}
    ]


def test_previous_month_uses_calendar_month_start_and_end(session):
    account = _account(session)
    today = date.today()
    current_start = today.replace(day=1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    session.add_all([
        Transaction(
            account_id=account.id,
            monobank_id="old-food",
            amount=-900,
            currency="UAH",
            date=previous_start,
            description="Old food",
            category=cat.FOOD_AND_DRINK,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="new-food",
            amount=-300,
            currency="UAH",
            date=current_start,
            description="New food",
            category=cat.FOOD_AND_DRINK,
        ),
    ])
    session.commit()

    summary = queries.get_month_cycle_summary(offset=1)

    assert summary["spending"]["period_start"] == previous_start.isoformat()
    assert summary["spending"]["period_end"] == previous_end.isoformat()
    assert summary["has_next"] is True
    assert summary["spending"]["rows"] == [
        {"category": cat.FOOD_AND_DRINK, "currency": "UAH", "amount": 900.0}
    ]


def test_previous_month_balance_is_as_of_selected_calendar_month_end(session):
    account = _account(session, balance=57_700)
    fop_usd = _account(session, is_fop=True, balance=700, currency="USD")
    today = date.today()
    current_start = today.replace(day=1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    session.add_all([
        Transaction(
            account_id=account.id,
            monobank_id="salary-prev",
            amount=40_000,
            currency="UAH",
            date=previous_start,
            description="Salary previous",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="after-income",
            amount=10_000,
            currency="UAH",
            date=current_start,
            description="After income",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=account.id,
            monobank_id="after-food",
            amount=-2_700,
            currency="UAH",
            date=current_start,
            description="After food",
            category=cat.FOOD_AND_DRINK,
        ),
        Transaction(
            account_id=fop_usd.id,
            monobank_id="salary-prev-usd",
            amount=500,
            currency="USD",
            date=previous_start,
            description="USD salary previous",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=fop_usd.id,
            monobank_id="after-usd-spend",
            amount=-100,
            currency="USD",
            date=current_start,
            description="After USD spend",
            category=cat.FINANCE,
        ),
    ])
    session.commit()

    summary = queries.get_month_cycle_summary(offset=1)

    assert summary["spending"]["period_end"] == previous_end.isoformat()
    assert summary["income"]["balances"] == {"UAH": 50_400, "USD": 800}


def test_month_income_uses_income_rules_and_exchange_rate(session):
    personal = _account(session)
    fop_usd = _account(session, is_fop=True, currency="USD")
    fop_uah = _account(session, is_fop=True, currency="UAH")
    start = date.today().replace(day=1)
    session.add(
        TransactionRule(
            rule_type="personal_income",
            pattern="STABIL GLOBAL",
            label="Stabil Global",
        )
    )
    session.add_all([
        Transaction(
            account_id=personal.id,
            monobank_id="internal-uah",
            amount=22_108.08,
            currency="UAH",
            date=start,
            description="UAH FOP internal transfer",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=fop_uah.id,
            monobank_id="internal-fop-uah",
            amount=22_108.08,
            currency="UAH",
            date=start,
            description="USD FOP internal transfer",
            category=cat.INCOME,
        ),
        Transaction(
            account_id=fop_usd.id,
            monobank_id="salary-usd",
            amount=500,
            currency="USD",
            date=start,
            description="From: STABIL GLOBAL LLC",
            category=cat.INCOME,
            extra={"exchange_rate": 44.21616},
        ),
        Transaction(
            account_id=personal.id,
            monobank_id="salary-personal",
            amount=22_108.08,
            currency="UAH",
            date=start + timedelta(days=1),
            description="STABIL GLOBAL LLC",
            category=cat.INCOME,
        ),
    ])
    session.commit()

    summary = queries.get_month_cycle_summary(offset=0)["income"]

    assert summary["usd_uah_rate"] == pytest.approx(44.21616)
    assert summary["by_currency"]["USD"]["fop"] == 500
    assert summary["by_currency"]["UAH"]["personal"] == pytest.approx(22_108.08)
    assert (
        summary["by_currency"]["UAH"]["personal_txns"][0]["description"]
        == "Stabil Global"
    )
    assert "UAH FOP internal transfer" not in str(summary)
    assert "USD FOP internal transfer" not in str(summary)


def test_spending_summary_excludes_fop_card_expenses(session):
    personal = _account(session)
    fop = _account(session, is_fop=True)
    start = date.today().replace(day=1)
    session.add_all([
        Transaction(
            account_id=personal.id,
            monobank_id="personal-finance",
            amount=-60_000,
            currency="UAH",
            date=start,
            description="Personal transfer",
            category=cat.FINANCE,
        ),
        Transaction(
            account_id=fop.id,
            monobank_id="fop-finance",
            amount=-117_928,
            currency="UAH",
            date=start,
            description="FOP transfer",
            category=cat.FINANCE,
        ),
    ])
    session.commit()

    summary = queries.get_spending_summary(offset=0)

    assert summary["rows"] == [
        {"category": cat.FINANCE, "currency": "UAH", "amount": 60_000.0}
    ]
    assert [tx["amount"] for tx in summary["details"][cat.FINANCE]] == [60_000.0]
