"""Manual transaction recording tests."""

from datetime import date

from sqlmodel import select

from finance_api.domains.accounts.models import Account
from finance_api.domains.transactions.models import Transaction


def test_record_manual_income_creates_hidden_manual_account_and_income_tx(
    session, monkeypatch
):
    import finance_api.domains.transactions.manual as manual

    monkeypatch.setattr(manual, "engine", session.bind)

    result = manual.record_manual_income(
        amount=1250,
        currency="USD",
        description="Cash consulting",
        received_on=date(2026, 6, 10),
        notes="recorded from chat",
    )

    assert result["amount"] == 1250
    assert result["currency"] == "USD"
    assert result["category"] == "Income"

    account = session.exec(select(Account)).one()
    assert account.monobank_id == "manual-income-USD"
    assert account.hidden is True

    tx = session.exec(select(Transaction)).one()
    assert tx.account_id == account.id
    assert tx.amount == 1250
    assert tx.currency == "USD"
    assert tx.description == "Cash consulting"
    assert tx.category == "Income"
    assert tx.notes == "recorded from chat"
    assert tx.extra == {"source": "manual_chat"}
