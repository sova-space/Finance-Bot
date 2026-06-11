"""Buy list domain queries."""

import uuid
from typing import Any

import structlog
from sqlmodel import Session, select

from finance_api.domains.buy_list.models import BuyListItem

log = structlog.get_logger(__name__)


def list_buy_list(session: Session, bought: str = "false") -> list[dict[str, Any]]:
    """Return buy list items filtered by purchased status.

    Args:
        session: Active database session.
        bought: "false" — only unbought (default); "true" — only bought;
                "all" — no filter.
    """
    q = select(BuyListItem)
    if bought == "false":
        q = q.where(BuyListItem.bought_at.is_(None))  # type: ignore[union-attr]
    elif bought == "true":
        q = q.where(BuyListItem.bought_at.is_not(None))  # type: ignore[union-attr]
    rows = session.exec(q).all()
    return [_to_dict(item) for item in rows]


def create_buy_list_item(
    session: Session,
    name: str,
    target_price: float | None,
    currency: str | None,
    url: str | None,
    notes: str | None,
) -> dict[str, Any]:
    """Insert a new buy list item and return its dict representation."""
    item = BuyListItem(
        name=name,
        target_price=target_price,
        currency=currency,
        url=url,
        notes=notes,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    log.info("buy_list_item_created", item_id=str(item.id), name=name)
    return _to_dict(item)


def update_buy_list_item(
    session: Session,
    item_id: uuid.UUID,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Apply partial updates to a buy list item. Returns None if not found."""
    item = session.get(BuyListItem, item_id)
    if item is None:
        return None
    for field, value in updates.items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return _to_dict(item)


def delete_buy_list_item(session: Session, item_id: uuid.UUID) -> bool:
    """Delete a buy list item by ID. Returns False if not found."""
    item = session.get(BuyListItem, item_id)
    if item is None:
        return False
    session.delete(item)
    session.commit()
    return True


def _to_dict(item: BuyListItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "name": item.name,
        "target_price": item.target_price,
        "currency": item.currency,
        "url": item.url,
        "notes": item.notes,
        "bought_at": item.bought_at.isoformat() if item.bought_at else None,
        "created_at": item.created_at.isoformat(),
    }
