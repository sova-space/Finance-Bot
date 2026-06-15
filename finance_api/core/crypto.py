"""Small encryption helpers for user-owned secrets."""

import base64
import hashlib

from cryptography.fernet import Fernet

from finance_api.core.config import settings


def _fernet() -> Fernet:
    if not settings.app_secret:
        raise RuntimeError("APP_SECRET is required to store user tokens")
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.app_secret.encode()).digest()
    )
    return Fernet(key)


def encrypt_text(value: str) -> str:
    """Encrypt a string for database storage."""
    return _fernet().encrypt(value.encode()).decode()


def decrypt_text(value: str) -> str:
    """Decrypt a string from database storage."""
    return _fernet().decrypt(value.encode()).decode()
