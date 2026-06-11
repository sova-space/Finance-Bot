"""Goals domain queries."""

import uuid
from typing import Any

import structlog
from sqlmodel import Session, select

from finance_api.domains.goals.models import Goal

log = structlog.get_logger(__name__)


def list_goals(session: Session) -> list[dict[str, Any]]:
    """Return all goals with progress ratio (current_amount / target_amount)."""
    goals = session.exec(select(Goal)).all()
    return [_to_dict(g) for g in goals]


def create_goal(
    session: Session,
    name: str,
    target_amount: float,
    currency: str,
    account_id: uuid.UUID | None,
    deadline: Any | None,
    notes: str | None,
) -> dict[str, Any]:
    """Insert a new goal and return its dict representation."""
    goal = Goal(
        name=name,
        target_amount=target_amount,
        currency=currency,
        account_id=account_id,
        deadline=deadline,
        notes=notes,
    )
    session.add(goal)
    session.commit()
    session.refresh(goal)
    log.info("goal_created", goal_id=str(goal.id), name=name)
    return _to_dict(goal)


def update_goal(
    session: Session,
    goal_id: uuid.UUID,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Apply partial updates to a goal. Returns None if not found."""
    goal = session.get(Goal, goal_id)
    if goal is None:
        return None
    for field, value in updates.items():
        setattr(goal, field, value)
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return _to_dict(goal)


def delete_goal(session: Session, goal_id: uuid.UUID) -> bool:
    """Delete a goal by ID. Returns False if not found."""
    goal = session.get(Goal, goal_id)
    if goal is None:
        return False
    session.delete(goal)
    session.commit()
    return True


def _to_dict(goal: Goal) -> dict[str, Any]:
    progress = (
        goal.current_amount / goal.target_amount if goal.target_amount > 0 else 0.0
    )
    return {
        "id": str(goal.id),
        "name": goal.name,
        "target_amount": goal.target_amount,
        "current_amount": goal.current_amount,
        "currency": goal.currency,
        "account_id": str(goal.account_id) if goal.account_id else None,
        "deadline": goal.deadline.isoformat() if goal.deadline else None,
        "notes": goal.notes,
        "achieved_at": goal.achieved_at.isoformat() if goal.achieved_at else None,
        "created_at": goal.created_at.isoformat(),
        "progress": round(progress, 4),
    }
