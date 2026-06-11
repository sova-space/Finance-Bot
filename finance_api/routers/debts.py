"""Debt endpoints."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from finance_api.core.auth.webapp import verify_webapp_user
from finance_api.core.db.engine import get_session
from finance_api.domains.debt import queries

router = APIRouter(
    prefix="/debts",
    tags=["debts"],
    dependencies=[Depends(verify_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]


class DebtCreate(BaseModel):
    """Request body for creating a debt."""

    person: str
    amount: float
    currency: str = "UAH"
    description: str | None = None
    due_date: str | None = None


class DebtPatch(BaseModel):
    """Request body for updating a debt."""

    person: str | None = None
    amount: float | None = None
    description: str | None = None
    due_date: str | None = None
    settled_at: str | None = None
    settled: bool | None = None


@router.get("", summary="List debts")
def list_debts(session: SessionDep, settled: str = "false") -> list[dict]:
    """List debts. Use `settled=false` (default), `true`, or `all`."""
    return queries.list_debts(session, settled=settled)


@router.post("", summary="Create a debt")
def create_debt(body: DebtCreate, session: SessionDep) -> dict:
    """Create a new debt record."""
    return queries.create_debt(
        session,
        person=body.person,
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        due_date=body.due_date,
    )


@router.patch("/{debt_id}", summary="Update a debt")
def patch_debt(debt_id: uuid.UUID, body: DebtPatch, session: SessionDep) -> dict:
    """Partially update a debt. Send `settled=true` to mark as settled now."""
    updates: dict = {}
    if body.person is not None:
        updates["person"] = body.person
    if body.amount is not None:
        updates["amount"] = body.amount
    if body.description is not None:
        updates["description"] = body.description
    if body.due_date is not None:
        updates["due_date"] = body.due_date
    if body.settled_at is not None:
        updates["settled_at"] = body.settled_at
    if body.settled is True:
        updates["settled_at"] = datetime.now(UTC).replace(tzinfo=None)

    result = queries.update_debt(session, debt_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Debt not found")
    return result


@router.delete("/{debt_id}", summary="Delete a debt")
def delete_debt(debt_id: uuid.UUID, session: SessionDep) -> dict:
    """Delete a debt. Returns 404 if not found."""
    if not queries.delete_debt(session, debt_id):
        raise HTTPException(status_code=404, detail="Debt not found")
    return {"deleted": True}
