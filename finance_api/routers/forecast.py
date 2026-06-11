"""Forecast, recurring, and income endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from finance_api.core.auth.webapp import verify_webapp_user
from finance_api.core.db.engine import get_session
from finance_api.domains.forecast import queries

SessionDep = Annotated[Session, Depends(get_session)]

# ---------------------------------------------------------------------------
# Forecast router
# ---------------------------------------------------------------------------

forecast_router = APIRouter(
    prefix="/forecast",
    tags=["forecast"],
    dependencies=[Depends(verify_webapp_user)],
)


@forecast_router.get("", summary="Monthly forecast")
def get_forecast(session: SessionDep) -> dict:
    """Return estimated end-of-month balance."""
    return queries.get_forecast(session)


# ---------------------------------------------------------------------------
# Recurring router
# ---------------------------------------------------------------------------

recurring_router = APIRouter(
    prefix="/recurring",
    tags=["recurring"],
    dependencies=[Depends(verify_webapp_user)],
)


class RecurringCreate(BaseModel):
    """Request body for creating a recurring item."""

    name: str
    amount: float
    currency: str = "UAH"
    day_of_month: int | None = None
    category: str | None = None


class RecurringPatch(BaseModel):
    """Request body for updating a recurring item."""

    name: str | None = None
    amount: float | None = None
    currency: str | None = None
    day_of_month: int | None = None
    category: str | None = None
    active: bool | None = None


@recurring_router.get("", summary="List recurring items")
def list_recurring(session: SessionDep) -> list[dict]:
    """Return all recurring expense items."""
    return queries.list_recurring(session)


@recurring_router.post("", summary="Create a recurring item")
def create_recurring(body: RecurringCreate, session: SessionDep) -> dict:
    """Create a recurring expense item."""
    return queries.create_recurring(
        session,
        name=body.name,
        amount=body.amount,
        currency=body.currency,
        day_of_month=body.day_of_month,
        category=body.category,
    )


@recurring_router.patch("/{item_id}", summary="Update a recurring item")
def patch_recurring(
    item_id: uuid.UUID, body: RecurringPatch, session: SessionDep
) -> dict:
    """Partially update a recurring item."""
    updates: dict = {}
    for field in ("name", "amount", "currency", "day_of_month", "category"):
        value = getattr(body, field)
        if value is not None:
            updates[field] = value
    if body.active is not None:
        updates["active"] = body.active

    result = queries.update_recurring(session, item_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Recurring item not found")
    return result


@recurring_router.delete("/{item_id}", summary="Delete a recurring item")
def delete_recurring(item_id: uuid.UUID, session: SessionDep) -> dict:
    """Delete a recurring item. Returns 404 if not found."""
    if not queries.delete_recurring(session, item_id):
        raise HTTPException(status_code=404, detail="Recurring item not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Income router
# ---------------------------------------------------------------------------

income_router = APIRouter(
    prefix="/income",
    tags=["income"],
    dependencies=[Depends(verify_webapp_user)],
)


class IncomeCreate(BaseModel):
    """Request body for creating an expected income item."""

    name: str
    amount: float
    currency: str = "UAH"
    day_of_month: int | None = None


class IncomePatch(BaseModel):
    """Request body for updating an expected income item."""

    name: str | None = None
    amount: float | None = None
    currency: str | None = None
    day_of_month: int | None = None
    active: bool | None = None


@income_router.get("", summary="List expected income items")
def list_income(session: SessionDep) -> list[dict]:
    """Return all expected income items."""
    return queries.list_income(session)


@income_router.post("", summary="Create an expected income item")
def create_income(body: IncomeCreate, session: SessionDep) -> dict:
    """Create an expected income item."""
    return queries.create_income(
        session,
        name=body.name,
        amount=body.amount,
        currency=body.currency,
        day_of_month=body.day_of_month,
    )


@income_router.patch("/{item_id}", summary="Update an expected income item")
def patch_income(item_id: uuid.UUID, body: IncomePatch, session: SessionDep) -> dict:
    """Partially update an expected income item."""
    updates: dict = {}
    for field in ("name", "amount", "currency", "day_of_month"):
        value = getattr(body, field)
        if value is not None:
            updates[field] = value
    if body.active is not None:
        updates["active"] = body.active

    result = queries.update_income(session, item_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Income item not found")
    return result


@income_router.delete("/{item_id}", summary="Delete an expected income item")
def delete_income(item_id: uuid.UUID, session: SessionDep) -> dict:
    """Delete an expected income item. Returns 404 if not found."""
    if not queries.delete_income(session, item_id):
        raise HTTPException(status_code=404, detail="Income item not found")
    return {"deleted": True}
