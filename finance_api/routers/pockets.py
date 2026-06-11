"""Pockets endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from finance_api.core.auth.webapp import verify_webapp_user
from finance_api.core.db.engine import get_session
from finance_api.domains.pockets import queries

router = APIRouter(
    prefix="/pockets",
    tags=["pockets"],
    dependencies=[Depends(verify_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]


class PocketCreate(BaseModel):
    """Request body for creating a pocket."""

    category: str
    monthly_budget: float
    currency: str = "UAH"
    emoji: str | None = None


class PocketPatch(BaseModel):
    """Request body for updating a pocket."""

    monthly_budget: float | None = None
    emoji: str | None = None
    balance: float | None = None


class TransferCreate(BaseModel):
    """Request body for creating a pocket transfer."""

    from_pocket_id: uuid.UUID | None = None
    to_pocket_id: uuid.UUID | None = None
    amount: float
    currency: str = "UAH"
    note: str | None = None


@router.get("", summary="List pockets")
def list_pockets(session: SessionDep) -> list[dict]:
    """Return all pockets."""
    return queries.list_pockets(session)


# IMPORTANT: /suggest must be declared before /{id} to prevent FastAPI from
# trying to parse the literal string "suggest" as a UUID.
@router.get("/suggest", summary="Suggest categories for new pockets")
def suggest_pockets(session: SessionDep) -> list[dict]:
    """Return categories with >3 months of spending history but no pocket."""
    return queries.suggest_pockets(session)


@router.post("", summary="Create a pocket", status_code=201)
def create_pocket(body: PocketCreate, session: SessionDep) -> dict:
    """Create a new pocket. Returns 409 if the category already has a pocket."""
    existing = queries.get_pocket_by_category(session, body.category)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Pocket for category '{body.category}' already exists",
        )
    pocket = queries.create_pocket(
        session,
        category=body.category,
        monthly_budget=body.monthly_budget,
        currency=body.currency,
        emoji=body.emoji,
    )
    return queries._to_dict(pocket)


@router.post("/transfer", summary="Transfer balance between pockets", status_code=201)
def create_transfer(body: TransferCreate, session: SessionDep) -> dict:
    """Create a pocket transfer and adjust balances."""
    if body.from_pocket_id is not None:
        if queries.get_pocket(session, body.from_pocket_id) is None:
            raise HTTPException(status_code=404, detail="Source pocket not found")
    if body.to_pocket_id is not None:
        if queries.get_pocket(session, body.to_pocket_id) is None:
            raise HTTPException(status_code=404, detail="Destination pocket not found")

    transfer = queries.create_transfer(
        session,
        from_pocket_id=body.from_pocket_id,
        to_pocket_id=body.to_pocket_id,
        amount=body.amount,
        currency=body.currency,
        note=body.note,
    )
    from_id = str(transfer.from_pocket_id) if transfer.from_pocket_id else None
    to_id = str(transfer.to_pocket_id) if transfer.to_pocket_id else None
    return {
        "id": str(transfer.id),
        "from_pocket_id": from_id,
        "to_pocket_id": to_id,
        "amount": transfer.amount,
        "currency": transfer.currency,
        "note": transfer.note,
        "created_at": transfer.created_at.isoformat(),
    }


@router.get("/{pocket_id}", summary="Get a pocket")
def get_pocket(pocket_id: uuid.UUID, session: SessionDep) -> dict:
    """Return a single pocket by ID."""
    pocket = queries.get_pocket(session, pocket_id)
    if pocket is None:
        raise HTTPException(status_code=404, detail="Pocket not found")
    return queries._to_dict(pocket)


@router.patch("/{pocket_id}", summary="Update a pocket")
def patch_pocket(pocket_id: uuid.UUID, body: PocketPatch, session: SessionDep) -> dict:
    """Partially update a pocket."""
    updates: dict = {}
    if body.monthly_budget is not None:
        updates["monthly_budget"] = body.monthly_budget
    if body.emoji is not None:
        updates["emoji"] = body.emoji
    if body.balance is not None:
        updates["balance"] = body.balance

    result = queries.update_pocket(session, pocket_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Pocket not found")
    return queries._to_dict(result)


@router.delete("/{pocket_id}", summary="Delete a pocket")
def delete_pocket(pocket_id: uuid.UUID, session: SessionDep) -> dict:
    """Delete a pocket. Returns 404 if not found."""
    if not queries.delete_pocket(session, pocket_id):
        raise HTTPException(status_code=404, detail="Pocket not found")
    return {"deleted": True}


@router.get("/{pocket_id}/transactions", summary="Transactions for a pocket")
def pocket_transactions(
    pocket_id: uuid.UUID,
    session: SessionDep,
    limit: int = 50,
) -> list[dict]:
    """Return transactions whose category matches the pocket's category."""
    pocket = queries.get_pocket(session, pocket_id)
    if pocket is None:
        raise HTTPException(status_code=404, detail="Pocket not found")
    return queries.get_pocket_transactions(session, pocket_id, limit=limit)
