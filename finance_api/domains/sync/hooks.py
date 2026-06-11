"""Hooks fired after new Monobank transactions are imported."""

from typing import Any

import structlog

from finance_api.core.config import settings
from finance_api.domains.bot.language import get_language
from finance_api.domains.bot.notifications import send_notification
from finance_api.domains.transactions import categories as cat

log = structlog.get_logger(__name__)

_CATEGORY_HINTS = {
    cat.FOOD_AND_DRINK: "you ate well 🍽️",
    cat.GROCERIES: "groceries run 🛒",
    cat.TRANSPORTATION: "moving around 🚇",
    cat.HEALTHCARE: "health spending 💊",
    cat.SHOPPING: "shopping 🛍️",
    cat.ENTERTAINMENT: "fun money 🎮",
    cat.TRAVEL: "travel ✈️",
    cat.SUBSCRIPTIONS: "subscription 🔁",
    cat.UTILITIES: "utilities 🏠",
    cat.ATM_CASH: "cash withdrawal 💵",
    cat.FINANCE: "finance fee/card move 💳",
    cat.EDUCATION: "learning 📚",
    cat.PETS: "pets 🐾",
    cat.PARTNER: "partner/couple spending 👥",
}

_UK_CATEGORY_HINTS = {
    cat.FOOD_AND_DRINK: "ото добре поїв 🍽️",
    cat.GROCERIES: "закупився 🛒",
    cat.TRANSPORTATION: "покатався 🚇",
    cat.HEALTHCARE: "здоровʼя 💊",
    cat.SHOPPING: "шопінг 🛍️",
    cat.ENTERTAINMENT: "розваги 🎮",
    cat.TRAVEL: "подорож ✈️",
    cat.SUBSCRIPTIONS: "підписка 🔁",
    cat.UTILITIES: "комуналка 🏠",
    cat.ATM_CASH: "готівка 💵",
    cat.FINANCE: "фінанси 💳",
    cat.EDUCATION: "навчання 📚",
    cat.PETS: "хвостики 🐾",
    cat.PARTNER: "спільні витрати 👥",
}

_CATEGORY_EXAMPLES = ", ".join([
    cat.FOOD_AND_DRINK,
    cat.GROCERIES,
    cat.TRANSPORTATION,
    cat.SHOPPING,
    cat.SUBSCRIPTIONS,
])


def _amount(tx: dict[str, Any]) -> str:
    amount = abs(float(tx["amount"]))
    if amount.is_integer():
        rendered = str(int(amount))
    else:
        rendered = f"{amount:.2f}"
    return f"{rendered} {tx['currency']}"


def format_new_transaction_message(tx: dict[str, Any]) -> str:
    """Human notification for one newly imported transaction."""
    language = get_language()
    description = tx["description"]
    category = tx.get("category")
    amount = _amount(tx)
    if category is None:
        if language == "uk":
            return (
                f"🆕 {description}: {amount}\n"
                "Що це за категорія? Напиши в чат, наприклад:\n"
                f"label {description} as Food & Drink\n"
                f"Варіанти: {_CATEGORY_EXAMPLES}"
            )
        return (
            f"🆕 {description}: {amount}\n"
            "What category is this? Reply in chat, e.g.\n"
            f"label {description} as Food & Drink\n"
            f"Options: {_CATEGORY_EXAMPLES}"
        )

    hints = _UK_CATEGORY_HINTS if language == "uk" else _CATEGORY_HINTS
    if category == cat.INCOME and float(tx["amount"]) >= 20000:
        if language == "uk":
            return f"🆕 {description}: {amount} — вау, зарплата, це круто 🎉"
        return f"🆕 {description}: {amount} — wow, salary day, it's cool 🎉"
    hint = hints.get(category, category)
    return f"🆕 {description}: {amount} — {hint}"


def notify_new_transactions(transactions: list[dict[str, Any]]) -> None:
    """Send Telegram notifications for newly imported transactions."""
    for tx in transactions:
        try:
            send_notification(
                format_new_transaction_message(tx),
                thread_id=settings.telegram_finance_topic_id,
            )
        except Exception as exc:
            log.warning(
                "new_transaction_notification_failed",
                description=tx.get("description"),
                error=str(exc),
            )
