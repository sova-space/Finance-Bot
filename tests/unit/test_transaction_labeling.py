"""Transaction labeling tests."""

from datetime import date

import pytest
from sqlmodel import select

from finance_api.domains.accounts.models import Account
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions.models import Transaction


def test_label_latest_uncategorized_transaction_updates_matching_tx(
    session, monkeypatch
):
    import finance_api.domains.transactions.labeling as labeling

    monkeypatch.setattr(labeling, "engine", session.bind)
    account = Account(
        monobank_id="acc-1",
        name="Card",
        currency="UAH",
        account_type="black",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    tx = Transaction(
        account_id=account.id,
        monobank_id="monobank_1",
        amount=-420,
        currency="UAH",
        date=date(2026, 6, 10),
        description="SHOCKO CAFE",
        category=None,
    )
    session.add(tx)
    session.commit()

    result = labeling.label_latest_uncategorized("shocko", cat.FOOD_AND_DRINK)

    assert result["description"] == "SHOCKO CAFE"
    assert result["category"] == cat.FOOD_AND_DRINK
    updated = session.exec(select(Transaction)).one()
    assert updated.category == cat.FOOD_AND_DRINK
    assert updated.mode == "solo"


def test_label_latest_uncategorized_rejects_unknown_category(session, monkeypatch):
    import finance_api.domains.transactions.labeling as labeling

    monkeypatch.setattr(labeling, "engine", session.bind)

    with pytest.raises(ValueError, match="Unknown category"):
        labeling.label_latest_uncategorized("x", "Eating Well")


def test_relabel_latest_transaction_updates_already_labeled_tx(session, monkeypatch):
    import finance_api.domains.transactions.labeling as labeling

    monkeypatch.setattr(labeling, "engine", session.bind)
    account = Account(
        monobank_id="acc-1",
        name="Card",
        currency="UAH",
        account_type="black",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    tx = Transaction(
        account_id=account.id,
        monobank_id="monobank_np",
        amount=-608.10,
        currency="UAH",
        date=date(2026, 6, 10),
        description="Нова пошта",
        category=cat.SHOPPING,
    )
    session.add(tx)
    session.commit()

    result = labeling.relabel_latest_transaction("нова", cat.COUPLE_TRANSFER)

    assert result["description"] == "Нова пошта"
    assert result["previous_category"] == cat.SHOPPING
    assert result["category"] == cat.COUPLE_TRANSFER
    updated = session.exec(select(Transaction)).one()
    assert updated.category == cat.COUPLE_TRANSFER


def test_edit_latest_transaction_can_adjust_amount_and_description(
    session, monkeypatch
):
    import finance_api.domains.transactions.labeling as labeling

    monkeypatch.setattr(labeling, "engine", session.bind)
    account = Account(
        monobank_id="acc-1",
        name="Card",
        currency="UAH",
        account_type="black",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    tx = Transaction(
        account_id=account.id,
        monobank_id="manual-income:1",
        amount=1000,
        currency="UAH",
        date=date(2026, 6, 10),
        description="Cash",
        category=cat.INCOME,
    )
    session.add(tx)
    session.commit()

    result = labeling.edit_latest_transaction(
        "cash",
        amount=1200,
        description="Cash income corrected",
        notes="fixed from chat",
    )

    assert result["amount"] == 1200
    assert result["description"] == "Cash income corrected"
    updated = session.exec(select(Transaction)).one()
    assert updated.amount == 1200
    assert updated.description == "Cash income corrected"
    assert updated.notes == "fixed from chat"
