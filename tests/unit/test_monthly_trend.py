"""Tests for monthly income/expense trend filtering."""

from datetime import date

from sqlmodel import Session

from finance_api.domains.accounts.models import Account
from finance_api.domains.insights.queries import get_monthly_trend
from finance_api.domains.transactions.categories import INCOME
from finance_api.domains.transactions.models import Transaction


def _make_account(session: Session) -> Account:
    account = Account(
        monobank_id="trend_account",
        name="Trend Account",
        currency="UAH",
        account_type="black",
        balance=0.0,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def test_monthly_trend_excludes_fop_card_internal_transfer(session: Session) -> None:
    """Internal FOP-to-card transfers must not inflate income charts."""
    account = _make_account(session)
    today = date.today()
    session.add(
        Transaction(
            account_id=account.id,
            monobank_id="real-income",
            amount=10_000,
            currency="UAH",
            date=today,
            description="COXIT",
            category=INCOME,
        )
    )
    session.add(
        Transaction(
            account_id=account.id,
            monobank_id="fop-usd-to-card-transfer",
            amount=50_000,
            currency="UAH",
            date=today,
            description="З доларового рахунку ФОП для переказу на картку",  # noqa: RUF001
            category=INCOME,
        )
    )
    session.add(
        Transaction(
            account_id=account.id,
            monobank_id="fop-uah-internal-transfer",
            amount=40_000,
            currency="UAH",
            date=today,
            description="З гривневого рахунку ФОП",  # noqa: RUF001
            category=INCOME,
        )
    )
    session.commit()

    trend = get_monthly_trend(months=1)

    assert trend == [
        {
            "month": today.strftime("%b %Y"),
            "currency": "UAH",
            "income": 10_000,
            "expenses": 0,
        }
    ]
