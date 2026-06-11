"""Debt domain model."""

import uuid
from datetime import UTC, date, datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Debt(SQLModel, table=True):
    """Money lent to or borrowed from a person."""

    __tablename__ = "debts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    person: str
    amount: float
    currency: str = "UAH"
    description: str | None = None
    due_date: date | None = None
    settled_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)
