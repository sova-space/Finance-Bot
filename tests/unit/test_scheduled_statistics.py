"""Scheduled statistics report tests."""

from datetime import date

from sqlmodel import Session

from finance_api.domains.accounts.models import Account
from finance_api.domains.insights import queries
from finance_api.domains.transactions.models import Transaction


def _tx(account_id, monobank_id, amount, tx_date, description, category):
    return Transaction(
        account_id=account_id,
        monobank_id=monobank_id,
        amount=amount,
        currency="UAH",
        date=tx_date,
        description=description,
        category=category,
    )


def test_daily_statistics_sums_today_income_and_expenses(session: Session):
    account = Account(
        monobank_id="black",
        name="Monobank Black UAH",
        currency="UAH",
        account_type="black",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    session.add(_tx(account.id, "expense", -500, date.today(), "Silpo", "Groceries"))
    session.add(_tx(account.id, "income", 1000, date.today(), "Salary", "Income"))
    session.add(_tx(account.id, "old", -300, date(2026, 1, 1), "Old", "Shopping"))
    session.commit()

    report = queries.get_daily_statistics()

    assert report["period_label"] == "Today"
    assert report["expenses_by_currency"] == {"UAH": 500}
    assert report["income_by_currency"] == {"UAH": 1000}
    assert report["category_rows"] == [
        {"category": "Groceries", "currency": "UAH", "amount": 500}
    ]


def test_statistics_report_formats_income_expense_and_total():
    text = queries.format_statistics_report({
        "period_label": "Today",
        "expenses_by_currency": {"UAH": 500},
        "income_by_currency": {"UAH": 1000},
        "category_rows": [{"category": "Groceries", "currency": "UAH", "amount": 500}],
    })

    assert "📊 <b>Today</b>" in text
    assert "- Expenses" in text
    assert "Groceries" in text
    assert "Total expenses: 500 ₴" in text
    assert "Total income: 1,000 ₴" in text
    assert "Total: 500 ₴" in text
