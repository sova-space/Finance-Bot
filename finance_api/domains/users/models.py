"""Application user model for hosted multi-user mode."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """Telegram user with optional encrypted Monobank token."""

    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    telegram_user_id: int = Field(unique=True, index=True)
    encrypted_monobank_token: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
