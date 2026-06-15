"""Hosted multi-user bot flow tests."""

from datetime import date

from sqlmodel import Session

from finance_api.domains.accounts.models import Account
from finance_api.domains.bot.handlers import _token_from_message, is_allowed_user
from finance_api.domains.insights.queries import get_account_balances
from finance_api.domains.transactions.models import Transaction
from finance_api.domains.users.queries import get_or_create_user_by_telegram_id


def test_private_users_are_allowed_without_owner_allowlist():
    assert is_allowed_user(42, chat_type="private")


def test_group_users_still_need_allowlist(monkeypatch):
    monkeypatch.setattr(
        "finance_api.domains.bot.handlers.settings.telegram_owner_id", 10
    )
    monkeypatch.setattr(
        "finance_api.domains.bot.handlers.settings.telegram_allowed_user_ids",
        "20",
        raising=False,
    )

    assert is_allowed_user(10, chat_type="group")
    assert is_allowed_user(20, chat_type="group")
    assert not is_allowed_user(30, chat_type="group")


def test_token_command_extracts_token_without_storing_plain_chat_noise():
    assert _token_from_message("/token abc123") == "abc123"
    assert _token_from_message("abc123") is None


def test_account_balance_can_be_scoped_to_user(session: Session):
    first = get_or_create_user_by_telegram_id(1)
    second = get_or_create_user_by_telegram_id(2)
    first_account = Account(
        user_id=first.id,
        monobank_id="first",
        name="First Black",
        currency="UAH",
        account_type="black",
        balance=100,
    )
    second_account = Account(
        user_id=second.id,
        monobank_id="second",
        name="Second Black",
        currency="UAH",
        account_type="black",
        balance=200,
    )
    session.add(first_account)
    session.add(second_account)
    session.commit()
    session.refresh(first_account)
    session.refresh(second_account)
    session.add(
        Transaction(
            user_id=first.id,
            account_id=first_account.id,
            monobank_id="tx-first",
            amount=-50,
            currency="UAH",
            date=date.today(),
            description="Groceries",
        )
    )
    session.add(
        Transaction(
            user_id=second.id,
            account_id=second_account.id,
            monobank_id="tx-second",
            amount=-150,
            currency="UAH",
            date=date.today(),
            description="Clothes",
        )
    )
    session.commit()

    balances = get_account_balances(user_id=first.id)

    assert [item["name"] for item in balances] == ["First Black"]
    assert balances[0]["spent"] == 50
