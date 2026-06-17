"""Public currency exchange rates."""

from time import monotonic
from typing import Any

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/fx", tags=["fx"])

_CURRENCY_CODES = {
    980: "UAH",
    840: "USD",
    978: "EUR",
    826: "GBP",
    756: "CHF",
    985: "PLN",
    203: "CZK",
}
_CACHE_TTL_SECONDS = 60 * 60
_cache: tuple[float, list[dict[str, object]]] | None = None


def _rate_value(row: dict[str, Any]) -> float | None:
    if row.get("rateCross"):
        return float(row["rateCross"])
    if row.get("rateSell"):
        return float(row["rateSell"])
    if row.get("rateBuy"):
        return float(row["rateBuy"])
    return None


@router.get("/rates")
def exchange_rates() -> list[dict[str, object]]:
    """Return Monobank public FX rates normalized to ISO currency codes."""
    global _cache
    now = monotonic()
    if _cache and now - _cache[0] < _CACHE_TTL_SECONDS:
        return _cache[1]

    response = httpx.get("https://api.monobank.ua/bank/currency", timeout=10)
    response.raise_for_status()
    normalized = []
    for row in response.json():
        from_currency = _CURRENCY_CODES.get(row.get("currencyCodeA"))
        to_currency = _CURRENCY_CODES.get(row.get("currencyCodeB"))
        rate = _rate_value(row)
        if from_currency and to_currency and rate:
            normalized.append(
                {
                    "from": from_currency,
                    "to": to_currency,
                    "rate": rate,
                    "date": row.get("date"),
                }
            )
    _cache = (now, normalized)
    return normalized
