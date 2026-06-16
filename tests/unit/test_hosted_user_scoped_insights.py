"""Hosted user scoped insight tests."""

from datetime import date

from sqlmodel import Session

from finance_api.domains.accounts.models import Account
from finance_api.domains.insights.queries import get_spending_summary
from finance_api.domains.transactions.models import Transaction
from finance_api.domains.users.queries import get_or_create_user_by_telegram_id


def _account(user_id, monobank_id):
    return Account(
        user_id=user_id,
        monobank_id=monobank_id,
        name=monobank_id,
        currency="UAH",
        account_type="black",
    )


def _tx(user_id, account_id, monobank_id, amount, category, description):
    return Transaction(
        user_id=user_id,
        account_id=account_id,
        monobank_id=monobank_id,
        amount=amount,
        currency="UAH",
        date=date.today(),
        description=description,
        category=category,
    )


def test_spending_summary_scopes_rows_and_details_to_user(session: Session):
    first = get_or_create_user_by_telegram_id(1)
    second = get_or_create_user_by_telegram_id(2)
    first_account = _account(first.id, "first")
    second_account = _account(second.id, "second")
    session.add(first_account)
    session.add(second_account)
    session.commit()
    session.refresh(first_account)
    session.refresh(second_account)
    session.add(_tx(first.id, first_account.id, "first-tx", -100, "Groceries", "Silpo"))
    session.add(
        _tx(second.id, second_account.id, "second-tx", -999, "Shopping", "Zara")
    )
    session.commit()

    summary = get_spending_summary(user_id=first.id)

    assert summary["rows"] == [
        {"category": "Groceries", "currency": "UAH", "amount": 100}
    ]
    assert list(summary["details"]) == ["Groceries"]
    assert summary["details"]["Groceries"][0]["description"] == "Silpo"


def test_spending_summary_uses_visible_accounts_like_balance(session: Session):
    user = get_or_create_user_by_telegram_id(1)
    personal = _account(user.id, "personal")
    fop = _account(user.id, "fop")
    fop.is_fop = True
    hidden = _account(user.id, "hidden")
    hidden.hidden = True
    session.add(personal)
    session.add(fop)
    session.add(hidden)
    session.commit()
    session.refresh(personal)
    session.refresh(fop)
    session.refresh(hidden)
    session.add(_tx(user.id, personal.id, "personal-tx", -100, "Groceries", "Silpo"))
    session.add(_tx(user.id, fop.id, "fop-tx", -200, "Finance", "Tax"))
    session.add(_tx(user.id, hidden.id, "hidden-tx", -300, "Shopping", "Hidden"))
    session.commit()

    summary = get_spending_summary(user_id=user.id)

    assert sorted(summary["rows"], key=lambda r: r["category"]) == [
        {"category": "Finance", "currency": "UAH", "amount": 200},
        {"category": "Groceries", "currency": "UAH", "amount": 100},
    ]
    assert sorted(summary["details"]) == ["Finance", "Groceries"]
