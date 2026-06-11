"""Goals domain model."""

import uuid
from datetime import UTC, date, datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Goal(SQLModel, table=True):
    """Savings goal with optional linked account and deadline."""

    __tablename__ = "goals"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    target_amount: float
    currency: str = "UAH"
    current_amount: float = 0.0
    account_id: uuid.UUID | None = None
    deadline: date | None = None
    notes: str | None = None
    achieved_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)
