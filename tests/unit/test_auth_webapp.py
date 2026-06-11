"""Unit tests for Telegram WebApp initData HMAC verification."""

import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException

from finance_api.core.auth.webapp import verify_webapp_user
from finance_api.core.config import get_settings

_BOT_TOKEN = "test_bot_token_123"
_OWNER_ID = 12345


def _build_init_data(
    user_id: int = _OWNER_ID,
    bot_token: str = _BOT_TOKEN,
    age_seconds: int = 0,
    tamper_hash: bool = False,
) -> str:
    """Build a valid (or optionally tampered) Telegram WebApp initData string."""
    auth_date = int(time.time()) - age_seconds
    user = json.dumps({"id": user_id, "first_name": "Test"})
    params = {
        "auth_date": str(auth_date),
        "user": user,
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()
    sig = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    if tamper_hash:
        sig = "0" * len(sig)
    params["hash"] = sig
    return urlencode(params)


def _make_request(auth_header: str | None) -> MagicMock:
    """Build a minimal mock FastAPI Request."""
    request = MagicMock()
    if auth_header is None:
        request.headers.get.return_value = None
    else:
        request.headers.get.return_value = auth_header
    return request


def _patch_settings(
    monkeypatch, bot_token: str | None = _BOT_TOKEN, owner_id: int = _OWNER_ID
):
    """Monkeypatch settings on the cached get_settings() instance."""
    s = get_settings()
    monkeypatch.setattr(s, "telegram_bot_token", bot_token)
    monkeypatch.setattr(s, "telegram_owner_id", owner_id)


def test_valid_initdata_returns_user_id(monkeypatch):
    """Valid initData with correct HMAC returns the owner's Telegram user ID."""
    _patch_settings(monkeypatch)
    init_data = _build_init_data()
    request = _make_request(f"tma {init_data}")

    result = verify_webapp_user(request)
    assert result == _OWNER_ID


def test_missing_authorization_header_raises_401(monkeypatch):
    """Missing Authorization header raises HTTP 401."""
    _patch_settings(monkeypatch)
    request = _make_request(None)

    with pytest.raises(HTTPException) as exc_info:
        verify_webapp_user(request)
    assert exc_info.value.status_code == 401


def test_tampered_hash_raises_401(monkeypatch):
    """Tampered HMAC hash raises HTTP 401."""
    _patch_settings(monkeypatch)
    init_data = _build_init_data(tamper_hash=True)
    request = _make_request(f"tma {init_data}")

    with pytest.raises(HTTPException) as exc_info:
        verify_webapp_user(request)
    assert exc_info.value.status_code == 401


def test_expired_auth_date_raises_401(monkeypatch):
    """initData older than 24 hours raises HTTP 401."""
    _patch_settings(monkeypatch)
    init_data = _build_init_data(age_seconds=86401)  # 24h + 1s
    request = _make_request(f"tma {init_data}")

    with pytest.raises(HTTPException) as exc_info:
        verify_webapp_user(request)
    assert exc_info.value.status_code == 401


def test_non_owner_user_raises_403(monkeypatch):
    """Valid initData but non-owner user ID raises HTTP 403."""
    _patch_settings(monkeypatch)
    init_data = _build_init_data(user_id=99999)  # not the owner
    request = _make_request(f"tma {init_data}")

    with pytest.raises(HTTPException) as exc_info:
        verify_webapp_user(request)
    assert exc_info.value.status_code == 403


def test_no_bot_token_raises_503(monkeypatch):
    """When telegram_bot_token is None, raises HTTP 503."""
    _patch_settings(monkeypatch, bot_token=None)
    request = _make_request("tma anything")

    with pytest.raises(HTTPException) as exc_info:
        verify_webapp_user(request)
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Bot token not configured"
