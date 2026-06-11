"""Trips domain model."""

import uuid
from datetime import UTC, date, datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Trip(SQLModel, table=True):
    """Per-trip spending budget with a date range."""

    __tablename__ = "trips"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    budget: float | None = None
    currency: str = "UAH"
    start_date: date
    end_date: date
    notes: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
