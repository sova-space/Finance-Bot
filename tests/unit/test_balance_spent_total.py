"""Balance formatter spent-total tests."""

from finance_api.domains.bot import formatter


def test_balance_shows_clear_spent_total_by_currency():
    text = formatter.format_balance(
        accounts=[
            {
                "name": "Monobank Black UAH",
                "currency": "UAH",
                "balance": 32765,
                "spent": 111856,
                "is_fop": False,
                "synced_at": None,
            },
            {
                "name": "Monobank White UAH",
                "currency": "UAH",
                "balance": 401,
                "spent": 0,
                "is_fop": False,
                "synced_at": None,
            },
            {
                "name": "Monobank FOP USD",
                "currency": "USD",
                "balance": 1,
                "spent": 2960,
                "is_fop": True,
                "synced_at": None,
            },
        ],
        month={
            "spending": {
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
            }
        },
    )

    assert "Spent" in text
    assert "🇺🇦 UAH  111,856 ₴" in text
    assert "🇺🇸 USD  $2,960" in text
