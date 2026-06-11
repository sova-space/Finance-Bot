"""Manual transaction recording helpers."""

import uuid
from datetime import date
from typing import Any

from sqlmodel import Session, select

from finance_api.core.db.engine import engine
from finance_api.domains.accounts.models import Account
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions.models import Transaction


def _manual_income_account(session: Session, currency: str) -> Account:
    monobank_id = f"manual-income-{currency.upper()}"
    account = session.exec(
        select(Account).where(Account.monobank_id == monobank_id)
    ).first()
    if account:
        return account

    account = Account(
        monobank_id=monobank_id,
        name=f"Manual income {currency.upper()}",
        currency=currency.upper(),
        account_type="manual",
        balance=0,
        hidden=True,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def record_manual_income(
    amount: float,
    currency: str,
    description: str,
    received_on: date | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Record non-Monobank income so summaries include it."""
    tx_date = received_on or date.today()
    normalized_currency = currency.upper()
    with Session(engine) as session:
        account = _manual_income_account(session, normalized_currency)
        tx = Transaction(
            account_id=account.id,
            monobank_id=f"manual-income:{uuid.uuid4()}",
            amount=abs(amount),
            currency=normalized_currency,
            date=tx_date,
            description=description.strip(),
            category=cat.INCOME,
            notes=notes,
            mode=None,
            extra={"source": "manual_chat"},
        )
        session.add(tx)
        session.commit()
        session.refresh(tx)
        return {
            "id": str(tx.id),
            "date": tx.date.isoformat(),
            "description": tx.description,
            "amount": tx.amount,
            "currency": tx.currency,
            "category": tx.category,
            "notes": tx.notes,
        }
