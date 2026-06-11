"""Buy list domain model."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class BuyListItem(SQLModel, table=True):
    """Wishlist item with optional target price."""

    __tablename__ = "buy_list_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    target_price: float | None = None
    currency: str | None = None
    url: str | None = None
    notes: str | None = None
    bought_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)
