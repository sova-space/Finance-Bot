"""User queries for hosted multi-user mode."""

import uuid

from sqlmodel import Session, select

from finance_api.core.crypto import decrypt_text, encrypt_text
from finance_api.core.db.engine import engine
from finance_api.domains.users.models import User


def get_or_create_user_by_telegram_id(telegram_user_id: int) -> User:
    """Return existing user or create one for a Telegram user ID."""
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.telegram_user_id == telegram_user_id)
        ).first()
        if user:
            return user
        user = User(telegram_user_id=telegram_user_id)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def save_monobank_token(user_id: uuid.UUID, token: str) -> None:
    """Encrypt and store a user's Monobank token."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user is None:
            raise ValueError("User not found")
        user.encrypted_monobank_token = encrypt_text(token)
        session.add(user)
        session.commit()


def get_monobank_token(user_id: uuid.UUID) -> str | None:
    """Return decrypted Monobank token for user, if configured."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user is None or not user.encrypted_monobank_token:
            return None
        return decrypt_text(user.encrypted_monobank_token)
