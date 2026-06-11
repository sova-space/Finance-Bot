"""Telegram WebApp initData HMAC verification dependency."""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.parse import parse_qsl

import structlog
from fastapi import HTTPException, Request

from finance_api.core.config import get_settings

log = structlog.get_logger(__name__)

_MAX_AGE_SECONDS = 86400  # 24 hours


def verify_webapp_user(request: Request) -> int:
    """Validate Telegram WebApp initData and return the caller's Telegram user ID.

    Raises:
        503 — bot token not configured.
        401 — missing/invalid Authorization header, tampered hash, expired auth_date,
              or any parse error.
        403 — authenticated user is not the owner.
    """
    settings = get_settings()

    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Bot token not configured")

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("tma "):
        log.info("webapp_auth_missing_header")
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    init_data_raw = auth_header[4:]  # strip "tma "

    try:
        params = dict(parse_qsl(init_data_raw, keep_blank_values=True))

        received_hash = params.get("hash")
        if not received_hash:
            raise ValueError("missing hash")

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(params.items()) if k != "hash"
        )

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=settings.telegram_bot_token.encode(),
            digestmod=hashlib.sha256,
        ).digest()

        expected_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            log.info("webapp_auth_invalid_hash")
            raise HTTPException(status_code=401, detail="Invalid initData hash")

        auth_date_str = params.get("auth_date")
        if not auth_date_str:
            raise ValueError("missing auth_date")

        auth_date = int(auth_date_str)
        now_ts = int(datetime.now(UTC).timestamp())
        if now_ts - auth_date > _MAX_AGE_SECONDS:
            log.info("webapp_auth_expired", age_seconds=now_ts - auth_date)
            raise HTTPException(status_code=401, detail="initData expired")

        user_json = params.get("user")
        if not user_json:
            raise ValueError("missing user field")

        user_data = json.loads(user_json)
        telegram_user_id = int(user_data["id"])

    except HTTPException:
        raise
    except Exception as exc:
        log.info("webapp_auth_parse_error", error=str(exc))
        raise HTTPException(status_code=401, detail="Invalid initData") from exc

    if telegram_user_id != settings.telegram_owner_id:
        log.info("webapp_auth_non_owner", user_id=telegram_user_id)
        raise HTTPException(status_code=403, detail="Not authorized")

    return telegram_user_id
