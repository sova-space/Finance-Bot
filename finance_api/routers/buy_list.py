"""Buy list endpoints."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from finance_api.core.auth.webapp import verify_webapp_user
from finance_api.core.db.engine import get_session
from finance_api.domains.buy_list import queries

router = APIRouter(
    prefix="/buy-list",
    tags=["buy-list"],
    dependencies=[Depends(verify_webapp_user)],
)

SessionDep = Annotated[Session, Depends(get_session)]


class BuyListItemCreate(BaseModel):
    """Request body for creating a buy list item."""

    name: str
    target_price: float | None = None
    currency: str | None = None
    url: str | None = None
    notes: str | None = None


class BuyListItemPatch(BaseModel):
    """Request body for updating a buy list item."""

    name: str | None = None
    target_price: float | None = None
    currency: str | None = None
    url: str | None = None
    notes: str | None = None
    bought: bool | None = None


@router.get("", summary="List buy list items")
def list_items(session: SessionDep, bought: str = "false") -> list[dict]:
    """List items. Use `bought=false` (default), `true`, or `all`."""
    return queries.list_buy_list(session, bought=bought)


@router.post("", summary="Create a buy list item")
def create_item(body: BuyListItemCreate, session: SessionDep) -> dict:
    """Add an item to the buy list."""
    return queries.create_buy_list_item(
        session,
        name=body.name,
        target_price=body.target_price,
        currency=body.currency,
        url=body.url,
        notes=body.notes,
    )


@router.patch("/{item_id}", summary="Update a buy list item")
def patch_item(item_id: uuid.UUID, body: BuyListItemPatch, session: SessionDep) -> dict:
    """Partially update a buy list item. Send `bought=true` to mark as purchased."""
    updates: dict = {}
    for field in ("name", "target_price", "currency", "url", "notes"):
        value = getattr(body, field)
        if value is not None:
            updates[field] = value
    if body.bought is True:
        updates["bought_at"] = datetime.now(UTC).replace(tzinfo=None)

    result = queries.update_buy_list_item(session, item_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.delete("/{item_id}", summary="Delete a buy list item")
def delete_item(item_id: uuid.UUID, session: SessionDep) -> dict:
    """Delete a buy list item. Returns 404 if not found."""
    if not queries.delete_buy_list_item(session, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return {"deleted": True}
