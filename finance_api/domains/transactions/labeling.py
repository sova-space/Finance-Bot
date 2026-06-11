"""Helpers for manually labeling uncategorized transactions from chat."""

from typing import Any

from sqlmodel import Session, select

from finance_api.core.db.engine import engine
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions import modes
from finance_api.domains.transactions.models import Transaction


def _find_latest_by_description(session: Session, description: str) -> Transaction:
    needle = description.strip().lower()
    if not needle:
        raise ValueError("Description is required")

    candidates = session.exec(
        select(Transaction)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())  # type: ignore[attr-defined]
        .limit(100)
    ).all()
    tx = next((t for t in candidates if needle in t.description.lower()), None)
    if tx is None:
        raise ValueError(f"No transaction matches '{description}'")
    return tx


def _tx_payload(tx: Transaction, **extra: Any) -> dict[str, Any]:
    return {
        "id": str(tx.id),
        "date": tx.date.isoformat(),
        "description": tx.description,
        "amount": tx.amount,
        "currency": tx.currency,
        "category": tx.category,
        "mode": tx.mode,
        "notes": tx.notes,
        **extra,
    }


def label_latest_uncategorized(description: str, category: str) -> dict[str, Any]:
    """Label the newest uncategorized transaction whose description matches."""
    if category not in cat.ALL:
        raise ValueError(f"Unknown category '{category}'. Valid: {sorted(cat.ALL)}")

    needle = description.strip().lower()
    if not needle:
        raise ValueError("Description is required")

    with Session(engine) as session:
        candidates = session.exec(
            select(Transaction)
            .where(Transaction.category.is_(None))  # type: ignore[union-attr]
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())  # type: ignore[attr-defined]
            .limit(50)
        ).all()
        tx = next((t for t in candidates if needle in t.description.lower()), None)
        if tx is None:
            raise ValueError(f"No uncategorized transaction matches '{description}'")

        tx.category = category
        if tx.amount < 0 and tx.mode is None:
            tx.mode = modes.SOLO
        session.add(tx)
        session.commit()
        session.refresh(tx)
        return _tx_payload(tx)


def relabel_latest_transaction(description: str, category: str) -> dict[str, Any]:
    """Change category for the newest transaction matching a description fragment."""
    if category not in cat.ALL:
        raise ValueError(f"Unknown category '{category}'. Valid: {sorted(cat.ALL)}")

    with Session(engine) as session:
        tx = _find_latest_by_description(session, description)
        previous = tx.category
        tx.category = category
        if tx.amount < 0 and tx.mode is None:
            tx.mode = modes.SOLO
        session.add(tx)
        session.commit()
        session.refresh(tx)
        return _tx_payload(tx, previous_category=previous)


def edit_latest_transaction(
    match: str,
    *,
    amount: float | None = None,
    description: str | None = None,
    category: str | None = None,
    date: str | None = None,
    notes: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Apply small chat-requested corrections to the latest matching transaction."""
    if category is not None and category not in cat.ALL:
        raise ValueError(f"Unknown category '{category}'. Valid: {sorted(cat.ALL)}")

    with Session(engine) as session:
        tx = _find_latest_by_description(session, match)
        if amount is not None:
            tx.amount = amount
        if description is not None:
            cleaned = description.strip()
            if not cleaned:
                raise ValueError("Description cannot be empty")
            tx.description = cleaned
        if category is not None:
            tx.category = category
        if date is not None:
            from datetime import date as date_type

            tx.date = date_type.fromisoformat(date)
        if notes is not None:
            tx.notes = notes
        if mode is not None:
            tx.mode = mode
        if tx.amount < 0 and tx.category is not None and tx.mode is None:
            tx.mode = modes.SOLO
        session.add(tx)
        session.commit()
        session.refresh(tx)
        return _tx_payload(tx)
