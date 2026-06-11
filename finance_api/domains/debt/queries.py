"""Debt domain queries."""

import uuid
from typing import Any

import structlog
from sqlmodel import Session, select

from finance_api.domains.debt.models import Debt

log = structlog.get_logger(__name__)


def list_debts(session: Session, settled: str = "false") -> list[dict[str, Any]]:
    """Return debts filtered by settlement status.

    Args:
        session: Active database session.
        settled: "false" — only open debts (default); "true" — only settled;
                 "all" — no filter.
    """
    q = select(Debt)
    if settled == "false":
        q = q.where(Debt.settled_at.is_(None))  # type: ignore[union-attr]
    elif settled == "true":
        q = q.where(Debt.settled_at.is_not(None))  # type: ignore[union-attr]
    rows = session.exec(q).all()
    return [_to_dict(d) for d in rows]


def create_debt(
    session: Session,
    person: str,
    amount: float,
    currency: str,
    description: str | None,
    due_date: Any | None,
) -> dict[str, Any]:
    """Insert a new debt record and return its dict representation."""
    debt = Debt(
        person=person,
        amount=amount,
        currency=currency,
        description=description,
        due_date=due_date,
    )
    session.add(debt)
    session.commit()
    session.refresh(debt)
    log.info("debt_created", debt_id=str(debt.id), person=person, amount=amount)
    return _to_dict(debt)


def update_debt(
    session: Session,
    debt_id: uuid.UUID,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Apply partial updates to a debt. Returns None if not found."""
    debt = session.get(Debt, debt_id)
    if debt is None:
        return None
    for field, value in updates.items():
        setattr(debt, field, value)
    session.add(debt)
    session.commit()
    session.refresh(debt)
    return _to_dict(debt)


def delete_debt(session: Session, debt_id: uuid.UUID) -> bool:
    """Delete a debt by ID. Returns False if not found."""
    debt = session.get(Debt, debt_id)
    if debt is None:
        return False
    session.delete(debt)
    session.commit()
    return True


def _to_dict(debt: Debt) -> dict[str, Any]:
    return {
        "id": str(debt.id),
        "person": debt.person,
        "amount": debt.amount,
        "currency": debt.currency,
        "description": debt.description,
        "due_date": debt.due_date.isoformat() if debt.due_date else None,
        "settled_at": debt.settled_at.isoformat() if debt.settled_at else None,
        "created_at": debt.created_at.isoformat(),
    }
