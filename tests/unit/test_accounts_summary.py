"""Tests for Accounts tab summary data."""

from datetime import date

from sqlmodel import Session

from finance_api.domains.accounts.manual_balances import ManualBalance
from finance_api.domains.accounts.models import Account
from finance_api.domains.insights.queries import get_accounts_summary
from finance_api.domains.transactions.categories import CASHBACK, INCOME
from finance_api.domains.transactions.models import Transaction
from finance_api.routers.accounts import delete_manual_balance, update_manual_balance
from finance_api.schemas import ManualBalanceCreate


def _account(monobank_id: str, balance: float = 0.0, hidden: bool = False) -> Account:
    return Account(
        monobank_id=monobank_id,
        name=monobank_id,
        currency="UAH",
        account_type="black",
        balance=balance,
        hidden=hidden,
    )


def _tx(
    account_id,
    monobank_id: str,
    amount: float,
    tx_date: date,
    category: str | None = INCOME,
    pending: bool = False,
) -> Transaction:
    return Transaction(
        account_id=account_id,
        monobank_id=monobank_id,
        amount=amount,
        currency="UAH",
        date=tx_date,
        description=monobank_id,
        category=category,
        is_pending=pending,
    )


def test_accounts_summary_returns_visible_buckets_and_income_totals(
    session: Session,
) -> None:
    """Accounts summary includes visible bank/manual rows and clean income totals."""
    today = date.today()
    visible = _account("black", balance=12000)
    credit = _account("credit", balance=-2500)
    hidden = _account("hidden", balance=999999, hidden=True)
    session.add(visible)
    session.add(credit)
    session.add(hidden)
    session.commit()
    session.refresh(visible)
    session.refresh(credit)
    session.refresh(hidden)

    session.add(
        ManualBalance(kind="cash", name="Cash wallet", currency="UAH", amount=5000)
    )
    session.add(
        ManualBalance(
            kind="asset",
            name="Car",
            currency="USD",
            amount=10000,
            ownership_percent=50,
        )
    )
    session.add(ManualBalance(kind="debt", name="Loan", currency="UAH", amount=3000))
    session.add(
        ManualBalance(
            kind="cash",
            name="Hidden cash",
            currency="UAH",
            amount=999,
            hidden=True,
        )
    )
    session.add(_tx(visible.id, "salary-month", 100000, today))
    session.add(_tx(visible.id, "salary-year", 200000, date(today.year, 1, 15)))
    session.add(_tx(visible.id, "cashback", 111, today, category=CASHBACK))
    session.add(_tx(visible.id, "pending", 222, today, pending=True))
    session.add(_tx(hidden.id, "hidden-income", 333, today))
    session.commit()

    summary = get_accounts_summary()

    assert [row["name"] for row in summary["bank_accounts"]] == ["black", "credit"]
    assert [row["name"] for row in summary["manual_balances"]] == [
        "Cash wallet",
        "Car",
        "Loan",
    ]
    assert summary["earnings"]["month"] == [{"currency": "UAH", "amount": 100000}]
    assert summary["earnings"]["year"] == [{"currency": "UAH", "amount": 300000}]


def test_manual_balance_rejects_unknown_kind() -> None:
    """Manual balance kind is constrained to the Accounts page buckets."""
    try:
        ManualBalance(kind="investment", name="ETF", currency="USD", amount=100)
    except ValueError as exc:
        assert "kind" in str(exc)
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("ManualBalance accepted an unsupported kind")


def test_manual_balance_can_be_updated_and_deleted(session: Session) -> None:
    """Manual Accounts rows can be maintained after creation."""
    row = ManualBalance(kind="cash", name="Cash", currency="UAH", amount=1000)
    session.add(row)
    session.commit()
    session.refresh(row)

    row_id = row.id
    updated = update_manual_balance(
        row_id,
        ManualBalanceCreate(
            kind="asset",
            name="Car",
            currency="USD",
            amount=9000,
            ownership_percent=50,
            note="shared",
        ),
    )

    assert updated["id"] == str(row_id)
    assert updated["kind"] == "asset"
    assert updated["name"] == "Car"
    assert updated["amount"] == 9000
    assert updated["ownership_percent"] == 50
    assert updated["note"] == "shared"

    deleted = delete_manual_balance(row_id)

    assert deleted == {"deleted": True}
    session.expire_all()
    assert session.get(ManualBalance, row_id) is None
