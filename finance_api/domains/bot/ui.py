"""Reusable Telegram UI payloads for finance views.

The standalone finance bot and Hermes' /finance command need the same one-message
inline UI. Keep the view rendering here and expose it over HTTP so Hermes does
not duplicate finance formatting logic.
"""

from typing import Any

from finance_api.domains.bot.formatter import (
    CATEGORY_EMOJI,
    format_balance,
    format_month_report,
    format_spending_category,
    format_spending_summary,
    format_subscriptions,
    format_sync_status,
)
from finance_api.domains.bot.handlers import (
    BALANCE_CALLBACK,
    MONTH_CALLBACK,
    SPENDING_CALLBACK,
    SPENDING_CAT_PREFIX,
    SUBS_CALLBACK,
    SYNC_CALLBACK,
)
from finance_api.domains.insights.queries import (
    get_account_balances,
    get_hidden_account_balances,
    get_income_summary,
    get_month_cycle_summary,
    get_spending_summary,
    get_subscriptions,
    get_sync_health,
    selected_month_label,
)
from finance_api.domains.transactions.categories import CASHBACK, COUPLE_TRANSFER

PARSE_MODE = "HTML"


def _button(
    text: str, callback_data: str | None = None, url: str | None = None
) -> dict[str, str]:
    payload = {"text": text}
    if callback_data is not None:
        payload["callback_data"] = callback_data
    if url is not None:
        payload["url"] = url
    return payload


def _callback(base: str, offset: int = 0) -> str:
    return f"{base}:{offset}"


def balance_keyboard(offset: int = 0) -> dict[str, list[list[dict[str, str]]]]:
    """Main finance inline keyboard as raw Telegram Bot API JSON."""
    return {
        "inline_keyboard": [
            [
                _button(
                    "💳 Balance", callback_data=_callback(BALANCE_CALLBACK, offset)
                ),
                _button(
                    f"📅 {selected_month_label(offset)}",
                    callback_data=_callback(MONTH_CALLBACK, offset),
                ),
            ],
            [
                _button(
                    "📊 Spending", callback_data=_callback(SPENDING_CALLBACK, offset)
                ),
                _button("🔄 Sync", callback_data=SYNC_CALLBACK),
            ],
        ]
    }


_CAT_SHORT: dict[str, str] = {
    "Food & Drink": "Food",
    "Groceries": "Groceries",
    "Transportation": "Transport",
    "Healthcare": "Health",
    "Shopping": "Shopping",
    "Entertainment": "Fun",
    "Travel": "Travel",
    "Subscriptions": "Subs",
    "Utilities": "Utils",
    "ATM & Cash": "Cash",
    "Finance": "Finance",
    "Education": "Education",
    "Pets": "Pets",
    "Partner": "Partner",
}


def spending_keyboard(data: dict[str, Any]) -> dict[str, list[list[dict[str, str]]]]:
    """Category drill-down buttons + back button as raw Telegram JSON."""
    rows_data = [
        r
        for r in data.get("rows", [])
        if r["currency"] == "UAH" and r["category"] not in {COUPLE_TRANSFER, CASHBACK}
    ]
    rows_data.sort(key=lambda r: r["amount"], reverse=True)
    offset = int(data.get("offset", 0))
    buttons = []
    for r in rows_data:
        category = r["category"]
        label = (
            f"{CATEGORY_EMOJI.get(category, '📦')} {_CAT_SHORT.get(category, category)}"
        )
        buttons.append(
            _button(label, callback_data=f"{SPENDING_CAT_PREFIX}{offset}:{category}")
        )
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    rows.append([
        _button("🔁 Subs", callback_data=_callback(SUBS_CALLBACK, offset)),
        _button("← Back", callback_data=_callback(BALANCE_CALLBACK, offset)),
    ])
    return {"inline_keyboard": rows}


def back_to_spending_keyboard(
    offset: int = 0,
) -> dict[str, list[list[dict[str, str]]]]:
    """Back button from a category detail view to the spending summary."""
    return {
        "inline_keyboard": [
            [_button("← Spending", callback_data=_callback(SPENDING_CALLBACK, offset))]
        ]
    }


def month_keyboard(summary: dict[str, Any]) -> dict[str, list[list[dict[str, str]]]]:
    """Month selector navigation + main menu back button."""
    offset = int(summary.get("offset", 0))
    month_row = [_button("← Prev", callback_data=f"month:{offset + 1}")]
    month_row.append(
        _button(f"📅 {selected_month_label(offset)}", callback_data=f"month:{offset}")
    )
    if summary.get("has_next"):
        month_row.append(_button("Next →", callback_data=f"month:{offset - 1}"))
    rows = [month_row]
    rows.append([_button("← Back", callback_data=_callback(BALANCE_CALLBACK, offset))])
    return {"inline_keyboard": rows}


def _offset_from_view(view: str) -> int:
    if ":" not in view:
        return 0
    try:
        return max(0, int(view.split(":", 1)[1]))
    except ValueError:
        return 0


def view_payload(view: str = "balance", category: str | None = None) -> dict[str, Any]:
    """Return a Telegram-ready UI payload for one finance view."""
    if view == "balance" or view.startswith("balance_cb:"):
        offset = _offset_from_view(view)
        accounts = get_account_balances()
        month = get_month_cycle_summary(offset)
        return {
            "text": format_balance(accounts, month),
            "parse_mode": PARSE_MODE,
            "reply_markup": balance_keyboard(offset),
        }

    if view == "skipped":
        accounts = get_hidden_account_balances()
        text = format_balance(accounts) if accounts else "No skipped accounts."
        return {
            "text": text,
            "parse_mode": PARSE_MODE,
            "reply_markup": balance_keyboard(),
        }

    if view == "income":
        text = (
            format_month_report(get_income_summary(), {})
            or "No income data for this month yet."
        )
        return {
            "text": text,
            "parse_mode": PARSE_MODE,
            "reply_markup": balance_keyboard(),
        }

    if view == "month":
        summary = get_month_cycle_summary()
        return {
            "text": f"📅 <b>Month</b>\n{selected_month_label(0)}",
            "parse_mode": PARSE_MODE,
            "reply_markup": month_keyboard(summary),
        }

    if view.startswith("month:"):
        summary = get_month_cycle_summary(int(view.split(":", 1)[1]))
        offset = int(summary["offset"])
        return {
            "text": f"📅 <b>Month</b>\n{selected_month_label(offset)}",
            "parse_mode": PARSE_MODE,
            "reply_markup": month_keyboard(summary),
        }

    if view == "spending" or view.startswith("spending:"):
        offset = _offset_from_view(view)
        data = get_spending_summary(offset)
        text = format_spending_summary(data) or "No spending recorded yet this month."
        return {
            "text": text,
            "parse_mode": PARSE_MODE,
            "reply_markup": spending_keyboard(data),
        }

    if view == "spending_category" and category:
        offset = 0
        if ":" in category:
            maybe_offset, category = category.split(":", 1)
            if maybe_offset.isdigit():
                offset = int(maybe_offset)
        data = get_spending_summary(offset)
        return {
            "text": format_spending_category(data, category),
            "parse_mode": PARSE_MODE,
            "reply_markup": back_to_spending_keyboard(offset),
        }

    if view == "subs" or view.startswith("subs:"):
        offset = _offset_from_view(view)
        return {
            "text": format_subscriptions(get_subscriptions(offset)),
            "parse_mode": PARSE_MODE,
            "reply_markup": spending_keyboard({"rows": [], "offset": offset}),
        }

    if view == "sync_status":
        return {
            "text": format_sync_status(get_sync_health()),
            "parse_mode": PARSE_MODE,
            "reply_markup": balance_keyboard(),
        }

    return {
        "text": "Unknown finance view.",
        "parse_mode": PARSE_MODE,
        "reply_markup": balance_keyboard(),
    }
