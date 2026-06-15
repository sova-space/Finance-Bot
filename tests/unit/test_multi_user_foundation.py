"""Hosted multi-user foundation tests."""

from sqlmodel import Session

from finance_api.domains.accounts.models import Account
from finance_api.domains.sync.monobank import _get_or_create_account, _parse_tx
from finance_api.domains.users.queries import (
    get_monobank_token,
    get_or_create_user_by_telegram_id,
    save_monobank_token,
)


def test_user_token_is_encrypted_at_rest(session: Session):
    user = get_or_create_user_by_telegram_id(123)

    save_monobank_token(user.id, "mono-secret-token")

    stored = session.get(type(user), user.id)
    assert stored is not None
    assert stored.encrypted_monobank_token != "mono-secret-token"
    assert get_monobank_token(user.id) == "mono-secret-token"


def test_same_monobank_account_id_can_exist_for_different_users(session: Session):
    first = get_or_create_user_by_telegram_id(1)
    second = get_or_create_user_by_telegram_id(2)

    first_account = _get_or_create_account(
        session,
        "same-mono-id",
        "Black",
        "UAH",
        "black",
        100,
        user_id=first.id,
    )
    second_account = _get_or_create_account(
        session,
        "same-mono-id",
        "Black",
        "UAH",
        "black",
        200,
        user_id=second.id,
    )

    assert first_account.id != second_account.id
    assert first_account.user_id == first.id
    assert second_account.user_id == second.id


def test_parsed_transactions_carry_user_id(session: Session):
    user = get_or_create_user_by_telegram_id(1)
    account = Account(
        user_id=user.id,
        monobank_id="mono-account",
        name="Black",
        currency="UAH",
        account_type="black",
    )
    session.add(account)
    session.commit()

    tx = _parse_tx(
        {
            "id": "tx-1",
            "amount": -12345,
            "currencyCode": 980,
            "time": 1_717_200_000,
            "description": "Silpo",
            "mcc": 5411,
        },
        account.id,
        "UAH",
        user_id=user.id,
    )

    assert tx is not None
    assert tx.user_id == user.id
