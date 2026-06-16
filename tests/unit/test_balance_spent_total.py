"""Balance formatter spent-total tests."""

from finance_api.domains.bot import formatter


def test_balance_does_not_duplicate_spent_totals():
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

    assert "<b>Spent</b>" not in text
    assert "🇺🇦 UAH  111,856 ₴" not in text
    assert "🇺🇸 USD  $2,960" not in text
    assert "Black  32,765 ₴ of 144,621 ₴ · spent 77%" in text
    assert "FOP  $1 of $2,961 · spent 100%" in text


def test_balance_uses_balance_now_title_and_skips_duplicate_currency_totals():
    text = formatter.format_balance(
        accounts=[
            {
                "name": "Monobank Black UAH",
                "currency": "UAH",
                "balance": 20862,
                "spent": 192069,
                "is_fop": False,
                "synced_at": None,
            },
            {
                "name": "Monobank White USD",
                "currency": "USD",
                "balance": 1,
                "spent": 0,
                "is_fop": False,
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

    assert text.startswith("💳 <b>Balance now</b>")
    assert "🇺🇦 UAH  <b>20,862 ₴</b>" not in text
    assert "🇺🇸 USD  <b>$1</b>" not in text
    assert "Black  20,862 ₴ of 212,931 ₴ · spent 90%" in text
    assert "White  $1" in text
