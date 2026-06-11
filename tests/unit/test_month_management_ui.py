"""Month management UI tests."""

from finance_api.domains.bot import formatter, ui


def test_balance_keyboard_has_month_management_button():
    keyboard = ui.balance_keyboard()["inline_keyboard"]

    assert any(
        button.get("callback_data") == "month:0" for row in keyboard for button in row
    )


def test_balance_keyboard_is_easy_to_tap():
    keyboard = ui.balance_keyboard()["inline_keyboard"]

    buttons = [button for row in keyboard for button in row]
    assert len(buttons) <= 6
    assert all(len(row) <= 2 for row in keyboard)


def test_month_report_formats_month_name_and_salary_range():
    text = formatter.format_month_report(
        income={
            "period_start": "2026-05-29",
            "by_currency": {
                "UAH": {
                    "fop": 0,
                    "personal": 40000,
                    "fop_txns": [],
                    "personal_txns": [
                        {
                            "date": "2026-05-29",
                            "amount": 40000,
                            "description": "Salary",
                        }
                    ],
                }
            },
            "balances": {"UAH": 10000},
        },
        spending={
            "period_start": "2026-05-29",
            "period_end": "2026-06-27",
            "rows": [
                {"category": "Food & Drink", "currency": "UAH", "amount": 2500},
            ],
            "details": {},
        },
    )

    assert "<b>Month · May</b>" in text
    assert "29 May-27 Jun" in text
    assert "Income" in text
    assert "Spending" in text
    assert "Food & Drink" in text


def test_balance_formats_configured_month():
    text = formatter.format_balance(
        accounts=[
            {
                "name": "Monobank Black UAH",
                "currency": "UAH",
                "balance": 10000,
                "is_fop": False,
                "synced_at": None,
            }
        ],
        month={
            "spending": {
                "period_start": "2026-06-05",
                "period_end": "2026-07-04",
            }
        },
    )

    assert "<b>Month · June</b>" in text
    assert "5 Jun-4 Jul" in text
    assert "Breakdown" not in text
    assert "Black" not in text


def test_income_summary_uses_short_heading():
    text = formatter.format_income_summary({
        "period_start": "2026-06-01",
        "by_currency": {
            "UAH": {
                "fop": 0,
                "personal": 40000,
                "fop_txns": [],
                "personal_txns": [
                    {
                        "date": "2026-06-02",
                        "amount": 40000,
                        "description": "Salary",
                    }
                ],
            },
            "USD": {
                "fop": 500,
                "personal": 0,
                "fop_txns": [
                    {
                        "date": "2026-06-01",
                        "amount": 500,
                        "description": "Salary USD",
                    }
                ],
                "personal_txns": [],
            },
        },
        "balances": {"UAH": 10000, "USD": 120},
        "usd_uah_rate": 40,
    })

    assert text.startswith("💰 <b>Income</b>")
    assert "Income ·" not in text
    assert "Received" not in text
    assert "🇺🇸" in text
    assert "$120" in text
    assert "<pre>" in text


def test_month_keyboard_has_previous_next_and_back_navigation():
    keyboard = ui.month_keyboard({
        "offset": 12,
        "has_previous": True,
        "has_next": True,
    })["inline_keyboard"]

    callbacks = [button["callback_data"] for row in keyboard for button in row]
    assert "month:13" in callbacks
    assert "month:12" in callbacks
    assert "month:11" in callbacks
    assert "balance_cb:12" in callbacks
