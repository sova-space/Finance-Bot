"""Forecast domain models: recurring expenses and expected income."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RecurringItem(SQLModel, table=True):
    """Monthly recurring expense used in end-of-month forecast."""

    __tablename__ = "recurring_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    amount: float
    currency: str = "UAH"
    day_of_month: int | None = None
    category: str | None = None
    active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)


class ExpectedIncomeItem(SQLModel, table=True):
    """Expected monthly income used in end-of-month forecast."""

    __tablename__ = "expected_income_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    amount: float
    currency: str = "UAH"
    day_of_month: int | None = None
    active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)
