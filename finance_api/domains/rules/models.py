"""Transaction classification rules stored in the database."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class TransactionRule(SQLModel, table=True):
    """Pattern-based rule for classifying or excluding transactions."""

    __tablename__ = "transaction_rules"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    rule_type: str  # 'personal_income' | 'passthrough' | 'partner_transfer'
    pattern: str  # case-insensitive substring match against description
    label: str  # display name shown in the bot
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
