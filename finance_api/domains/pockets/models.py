"""Pockets domain models."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Pocket(SQLModel, table=True):
    """Visual budget container for a spending category."""

    __tablename__ = "pockets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category: str = Field(unique=True)
    monthly_budget: float
    currency: str = "UAH"
    balance: float = 0.0
    emoji: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class PocketTransfer(SQLModel, table=True):
    """Manual balance transfer between pockets."""

    __tablename__ = "pocket_transfers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    from_pocket_id: uuid.UUID | None = Field(default=None, foreign_key="pockets.id")
    to_pocket_id: uuid.UUID | None = Field(default=None, foreign_key="pockets.id")
    amount: float
    currency: str = "UAH"
    note: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
