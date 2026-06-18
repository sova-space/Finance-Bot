"""Monobank comment-driven autolabeling tests."""

from datetime import date

from sqlmodel import Session, select

from finance_api.domains.accounts.models import Account
from finance_api.domains.rules.models import TransactionRule
from finance_api.domains.sync.monobank import _parse_tx, _sync_parsed_transaction
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions.models import Transaction
from finance_api.domains.trips.models import Trip


def _account(session: Session) -> Account:
    account = Account(
        monobank_id="acc-1",
        name="Card",
        currency="UAH",
        account_type="black",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def test_comment_category_labels_transaction_and_learns_receiver_rule(session: Session):
    account = _account(session)
    parsed = _parse_tx(
        {
            "id": "badboy-1",
            "amount": -69000,
            "currencyCode": 980,
            "time": 1_717_200_000,
            "description": "BadBoy",
            "comment": "alcohol",
        },
        account.id,
        "UAH",
    )

    assert parsed is not None
    _sync_parsed_transaction(session, parsed)
    session.commit()

    tx = session.exec(select(Transaction)).one()
    assert tx.category == cat.FOOD_AND_DRINK
    assert tx.notes == "alcohol"
    rule = session.exec(select(TransactionRule)).one()
    assert rule.rule_type == "auto_category"
    assert rule.pattern == "BadBoy"
    assert rule.label == cat.FOOD_AND_DRINK


def test_learned_receiver_rule_labels_future_transactions_without_comment(
    session: Session,
):
    account = _account(session)
    session.add(
        TransactionRule(
            rule_type="auto_category",
            pattern="BadBoy",
            label=cat.FOOD_AND_DRINK,
        )
    )
    session.commit()

    parsed = _parse_tx(
        {
            "id": "badboy-2",
            "amount": -120000,
            "currencyCode": 980,
            "time": 1_717_200_000,
            "description": "BadBoy",
            "mcc": 5411,
        },
        account.id,
        "UAH",
    )

    assert parsed is not None
    _sync_parsed_transaction(session, parsed)
    session.commit()

    tx = session.exec(select(Transaction)).one()
    assert tx.category == cat.FOOD_AND_DRINK


def test_resync_detects_comment_added_after_transaction_was_imported(
    session: Session,
):
    account = _account(session)
    original = Transaction(
        account_id=account.id,
        monobank_id="monobank_late-comment",
        amount=-450,
        currency="UAH",
        date=date(2026, 6, 18),
        description="BadBoy",
        category=None,
        notes=None,
    )
    session.add(original)
    session.commit()

    parsed = _parse_tx(
        {
            "id": "late-comment",
            "amount": -45000,
            "currencyCode": 980,
            "time": 1_718_668_800,
            "description": "BadBoy",
            "comment": "alcohol",
        },
        account.id,
        "UAH",
    )

    assert parsed is not None
    _sync_parsed_transaction(session, parsed)
    session.commit()

    updated = session.exec(select(Transaction)).one()
    assert updated.notes == "alcohol"
    assert updated.category == cat.FOOD_AND_DRINK


def test_comment_can_attach_transaction_to_matching_trip(session: Session):
    account = _account(session)
    session.add(
        Trip(
            name="Paris",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            budget=1000,
            currency="EUR",
        )
    )
    session.commit()

    parsed = _parse_tx(
        {
            "id": "paris-1",
            "amount": -250000,
            "currencyCode": 978,
            "time": 1_718_668_800,
            "description": "HOTEL",
            "comment": "Paris hotel",
        },
        account.id,
        "EUR",
    )

    assert parsed is not None
    _sync_parsed_transaction(session, parsed)
    session.commit()

    tx = session.exec(select(Transaction)).one()
    assert tx.category == cat.TRAVEL
    assert tx.extra == {"trip": "Paris"}
