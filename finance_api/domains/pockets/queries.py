"""Pockets domain queries."""

import uuid
from datetime import date, timedelta
from typing import Any

import structlog
from sqlmodel import Session, select

from finance_api.domains.pockets.models import Pocket, PocketTransfer
from finance_api.domains.transactions.models import Transaction

log = structlog.get_logger(__name__)


def list_pockets(session: Session) -> list[dict[str, Any]]:
    """Return all pockets ordered by category."""
    rows = session.exec(select(Pocket).order_by(Pocket.category)).all()
    return [_to_dict(p) for p in rows]


def get_pocket(session: Session, pocket_id: uuid.UUID) -> Pocket | None:
    """Return a pocket by primary key."""
    return session.get(Pocket, pocket_id)


def get_pocket_by_category(session: Session, category: str) -> Pocket | None:
    """Return the pocket for a given category, or None."""
    return session.exec(select(Pocket).where(Pocket.category == category)).first()


def create_pocket(
    session: Session,
    category: str,
    monthly_budget: float,
    currency: str = "UAH",
    emoji: str | None = None,
) -> Pocket:
    """Insert a new pocket. Sets balance = monthly_budget."""
    pocket = Pocket(
        category=category,
        monthly_budget=monthly_budget,
        currency=currency,
        balance=monthly_budget,
        emoji=emoji,
    )
    session.add(pocket)
    session.commit()
    session.refresh(pocket)
    log.info(
        "pocket_created",
        pocket_id=str(pocket.id),
        category=category,
        monthly_budget=monthly_budget,
    )
    return pocket


def update_pocket(
    session: Session,
    pocket_id: uuid.UUID,
    updates: dict[str, Any],
) -> Pocket | None:
    """Apply partial updates to a pocket. Returns None if not found."""
    pocket = session.get(Pocket, pocket_id)
    if pocket is None:
        return None
    for field, value in updates.items():
        setattr(pocket, field, value)
    session.add(pocket)
    session.commit()
    session.refresh(pocket)
    return pocket


def delete_pocket(session: Session, pocket_id: uuid.UUID) -> bool:
    """Delete a pocket by ID. Returns False if not found."""
    pocket = session.get(Pocket, pocket_id)
    if pocket is None:
        return False
    session.delete(pocket)
    session.commit()
    return True


def drain_pocket(
    session: Session,
    category: str,
    amount: float,
    currency: str,
) -> None:
    """Subtract amount from the matching pocket's balance (floor at 0).

    No-op if no pocket exists for the given category+currency combination.
    """
    pocket = get_pocket_by_category(session, category)
    if pocket is None:
        return
    if pocket.currency != currency:
        return
    pocket.balance = max(0.0, pocket.balance - amount)
    session.add(pocket)
    session.commit()
    log.info(
        "pocket_drained",
        pocket_id=str(pocket.id),
        category=category,
        amount=amount,
        balance=pocket.balance,
    )


def reset_all_pockets(session: Session) -> int:
    """Reset all pockets' balance to their monthly_budget. Returns count updated."""
    pockets = session.exec(select(Pocket)).all()
    count = 0
    for pocket in pockets:
        pocket.balance = pocket.monthly_budget
        session.add(pocket)
        count += 1
    if count:
        session.commit()
    log.info("pockets_reset", count=count)
    return count


def create_transfer(
    session: Session,
    from_pocket_id: uuid.UUID | None,
    to_pocket_id: uuid.UUID | None,
    amount: float,
    currency: str,
    note: str | None,
) -> PocketTransfer:
    """Record a transfer and adjust pocket balances accordingly."""
    if from_pocket_id is not None:
        from_pocket = session.get(Pocket, from_pocket_id)
        if from_pocket is not None:
            from_pocket.balance = max(0.0, from_pocket.balance - amount)
            session.add(from_pocket)

    if to_pocket_id is not None:
        to_pocket = session.get(Pocket, to_pocket_id)
        if to_pocket is not None:
            to_pocket.balance += amount
            session.add(to_pocket)

    transfer = PocketTransfer(
        from_pocket_id=from_pocket_id,
        to_pocket_id=to_pocket_id,
        amount=amount,
        currency=currency,
        note=note,
    )
    session.add(transfer)
    session.commit()
    session.refresh(transfer)
    log.info(
        "pocket_transfer_created",
        transfer_id=str(transfer.id),
        from_pocket_id=str(from_pocket_id),
        to_pocket_id=str(to_pocket_id),
        amount=amount,
    )
    return transfer


def suggest_pockets(session: Session) -> list[dict[str, Any]]:
    """Return categories with >3 months of spending history but no pocket yet.

    Checks the last 6 calendar months. A category qualifies if it appears
    in more than 3 distinct months.
    """
    today = date.today()
    monthly_categories: dict[str, int] = {}

    for offset in range(6):
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        first = date(year, month, 1)
        if month == 12:
            last = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last = date(year, month + 1, 1) - timedelta(days=1)

        rows = session.exec(
            select(Transaction.category)
            .where(Transaction.date >= first)
            .where(Transaction.date <= last)
            .where(Transaction.amount < 0)
            .where(Transaction.category.is_not(None))  # type: ignore[union-attr]
            .distinct()
        ).all()

        for cat in rows:
            if cat:
                monthly_categories[cat] = monthly_categories.get(cat, 0) + 1

    existing_categories = {
        p.category for p in session.exec(select(Pocket.category)).all()
    }

    suggestions = [
        {"category": cat, "months_with_spending": count}
        for cat, count in monthly_categories.items()
        if count > 3 and cat not in existing_categories
    ]
    suggestions.sort(key=lambda x: x["months_with_spending"], reverse=True)
    return suggestions


def get_pocket_transactions(
    session: Session,
    pocket_id: uuid.UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return transactions matching the pocket's category."""
    pocket = session.get(Pocket, pocket_id)
    if pocket is None:
        return []
    rows = session.exec(
        select(Transaction)
        .where(Transaction.category == pocket.category)
        .order_by(Transaction.date.desc())  # type: ignore[union-attr]
        .limit(limit)
    ).all()
    return [
        {
            "id": str(t.id),
            "amount": t.amount,
            "currency": t.currency,
            "date": t.date.isoformat(),
            "description": t.description,
            "category": t.category,
            "is_pending": t.is_pending,
        }
        for t in rows
    ]


def _to_dict(pocket: Pocket) -> dict[str, Any]:
    return {
        "id": str(pocket.id),
        "category": pocket.category,
        "monthly_budget": pocket.monthly_budget,
        "currency": pocket.currency,
        "balance": pocket.balance,
        "emoji": pocket.emoji,
        "created_at": pocket.created_at.isoformat(),
    }
