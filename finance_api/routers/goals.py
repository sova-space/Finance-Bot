"""Goals endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from finance_api.core.auth.webapp import verify_webapp_user
from finance_api.core.db.engine import get_session
from finance_api.domains.goals import queries

router = APIRouter(
    prefix="/goals",
    tags=["goals"],
    dependencies=[Depends(verify_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]


class GoalCreate(BaseModel):
    """Request body for creating a goal."""

    name: str
    target_amount: float
    currency: str = "UAH"
    account_id: uuid.UUID | None = None
    deadline: str | None = None
    notes: str | None = None


class GoalPatch(BaseModel):
    """Request body for updating a goal."""

    name: str | None = None
    target_amount: float | None = None
    current_amount: float | None = None
    currency: str | None = None
    account_id: uuid.UUID | None = None
    deadline: str | None = None
    notes: str | None = None
    achieved_at: str | None = None


@router.get("", summary="List goals")
def list_goals(session: SessionDep) -> list[dict]:
    """Return all goals with progress."""
    return queries.list_goals(session)


@router.post("", summary="Create a goal")
def create_goal(body: GoalCreate, session: SessionDep) -> dict:
    """Create a new savings goal."""
    return queries.create_goal(
        session,
        name=body.name,
        target_amount=body.target_amount,
        currency=body.currency,
        account_id=body.account_id,
        deadline=body.deadline,
        notes=body.notes,
    )


@router.patch("/{goal_id}", summary="Update a goal")
def patch_goal(goal_id: uuid.UUID, body: GoalPatch, session: SessionDep) -> dict:
    """Partially update a goal."""
    updates: dict = {}
    for field in (
        "name",
        "target_amount",
        "current_amount",
        "currency",
        "account_id",
        "deadline",
        "notes",
        "achieved_at",
    ):
        value = getattr(body, field)
        if value is not None:
            updates[field] = value

    result = queries.update_goal(session, goal_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return result


@router.delete("/{goal_id}", summary="Delete a goal")
def delete_goal(goal_id: uuid.UUID, session: SessionDep) -> dict:
    """Delete a goal. Returns 404 if not found."""
    if not queries.delete_goal(session, goal_id):
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"deleted": True}
