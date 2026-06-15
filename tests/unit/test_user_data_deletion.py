"""Hosted user deletion tests."""

from datetime import date

from sqlmodel import Session, select

from finance_api.domains.accounts.models import Account
from finance_api.domains.transactions.models import Transaction
from finance_api.domains.users.models import User
from finance_api.domains.users.queries import (
    delete_user_data,
    get_or_create_user_by_telegram_id,
    save_monobank_token,
)


def _account(user_id, monobank_id, balance=0):
    return Account(
        user_id=user_id,
        monobank_id=monobank_id,
        name=monobank_id,
        currency="UAH",
        account_type="black",
        balance=balance,
    )


def test_delete_user_data_removes_only_that_users_private_finance_data(
    session: Session,
):
    first = get_or_create_user_by_telegram_id(1)
    second = get_or_create_user_by_telegram_id(2)
    save_monobank_token(first.id, "first-token")
    save_monobank_token(second.id, "second-token")

    first_account = _account(first.id, "first-account")
    second_account = _account(second.id, "second-account")
    session.add(first_account)
    session.add(second_account)
    session.commit()
    session.refresh(first_account)
    session.refresh(second_account)
    session.add(
        Transaction(
            user_id=first.id,
            account_id=first_account.id,
            monobank_id="first-tx",
            amount=-100,
            currency="UAH",
            date=date.today(),
            description="first",
        )
    )
    session.add(
        Transaction(
            user_id=second.id,
            account_id=second_account.id,
            monobank_id="second-tx",
            amount=-200,
            currency="UAH",
            date=date.today(),
            description="second",
        )
    )
    session.commit()

    deleted = delete_user_data(first.id)

    assert deleted == {"transactions": 1, "accounts": 1, "user": 1}
    assert session.get(User, first.id) is None
    assert session.get(User, second.id) is not None
    remaining = session.exec(select(Transaction)).all()
    assert [tx.monobank_id for tx in remaining] == ["second-tx"]
