"""Manual account-bucket balances for the Accounts page."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import field_validator
from sqlmodel import Field, SQLModel

ManualBalanceKind = Literal["cash", "asset", "debt"]
VALID_MANUAL_BALANCE_KINDS = {"cash", "asset", "debt"}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ManualBalance(SQLModel, table=True):
    """Manual cash, ownership/asset, or debt row shown on Accounts tab."""

    __tablename__ = "manual_balances"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    kind: str = Field(index=True)
    name: str
    currency: str = "UAH"
    amount: float
    ownership_percent: float = 100.0
    note: str | None = None
    hidden: bool = False
    updated_at: datetime = Field(default_factory=_utcnow)

    def __init__(self, **data: object) -> None:
        super().__init__(**data)
        self._validate_kind(self.kind)
        self._validate_amount(self.amount)
        self._validate_ownership_percent(self.ownership_percent)

    @field_validator("kind")
    @classmethod
    def _validate_kind(cls, value: str) -> str:
        if value not in VALID_MANUAL_BALANCE_KINDS:
            raise ValueError("kind must be one of: cash, asset, debt")
        return value

    @field_validator("amount")
    @classmethod
    def _validate_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("amount must be non-negative")
        return value

    @field_validator("ownership_percent")
    @classmethod
    def _validate_ownership_percent(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("ownership_percent must be between 0 and 100")
        return value
