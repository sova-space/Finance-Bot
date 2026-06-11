"""Forecast domain queries."""

import uuid
from calendar import monthrange
from datetime import date
from typing import Any

import structlog
from sqlmodel import Session, select

from finance_api.domains.accounts.models import Account
from finance_api.domains.forecast.models import ExpectedIncomeItem, RecurringItem
from finance_api.domains.insights.queries import get_spending_by_category

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Recurring items
# ---------------------------------------------------------------------------


def list_recurring(session: Session, active_only: bool = False) -> list[dict[str, Any]]:
    """Return recurring expense items."""
    q = select(RecurringItem)
    if active_only:
        q = q.where(RecurringItem.active == True)  # noqa: E712
    rows = session.exec(q).all()
    return [_recurring_to_dict(r) for r in rows]


def create_recurring(
    session: Session,
    name: str,
    amount: float,
    currency: str,
    day_of_month: int | None,
    category: str | None,
) -> dict[str, Any]:
    """Insert a recurring item and return its dict representation."""
    item = RecurringItem(
        name=name,
        amount=amount,
        currency=currency,
        day_of_month=day_of_month,
        category=category,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    log.info("recurring_created", item_id=str(item.id), name=name)
    return _recurring_to_dict(item)


def update_recurring(
    session: Session,
    item_id: uuid.UUID,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Apply partial updates to a recurring item. Returns None if not found."""
    item = session.get(RecurringItem, item_id)
    if item is None:
        return None
    for field, value in updates.items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return _recurring_to_dict(item)


def delete_recurring(session: Session, item_id: uuid.UUID) -> bool:
    """Delete a recurring item by ID. Returns False if not found."""
    item = session.get(RecurringItem, item_id)
    if item is None:
        return False
    session.delete(item)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Expected income items
# ---------------------------------------------------------------------------


def list_income(session: Session, active_only: bool = False) -> list[dict[str, Any]]:
    """Return expected income items."""
    q = select(ExpectedIncomeItem)
    if active_only:
        q = q.where(ExpectedIncomeItem.active == True)  # noqa: E712
    rows = session.exec(q).all()
    return [_income_to_dict(i) for i in rows]


def create_income(
    session: Session,
    name: str,
    amount: float,
    currency: str,
    day_of_month: int | None,
) -> dict[str, Any]:
    """Insert an expected income item and return its dict representation."""
    item = ExpectedIncomeItem(
        name=name,
        amount=amount,
        currency=currency,
        day_of_month=day_of_month,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    log.info("income_created", item_id=str(item.id), name=name)
    return _income_to_dict(item)


def update_income(
    session: Session,
    item_id: uuid.UUID,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    """Apply partial updates to an expected income item. Returns None if not found."""
    item = session.get(ExpectedIncomeItem, item_id)
    if item is None:
        return None
    for field, value in updates.items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return _income_to_dict(item)


def delete_income(session: Session, item_id: uuid.UUID) -> bool:
    """Delete an expected income item by ID. Returns False if not found."""
    item = session.get(ExpectedIncomeItem, item_id)
    if item is None:
        return False
    session.delete(item)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Forecast computation
# ---------------------------------------------------------------------------


def get_forecast(session: Session) -> dict[str, Any]:
    """Compute end-of-month forecast.

    Returns:
        balances: current account balances, one entry per account.
        recurring: active recurring expense items.
        income: active expected income items.
        projected_variable_spend: run-rate per currency.
        forecast_by_currency: estimated month-end balance per currency.
    """
    today = date.today()
    days_in_month = monthrange(today.year, today.month)[1]
    days_elapsed = today.day

    # Current account balances grouped by currency
    accounts = session.exec(select(Account)).all()
    balances_by_currency: dict[str, float] = {}
    balance_details = []
    for acc in accounts:
        balances_by_currency[acc.currency] = (
            balances_by_currency.get(acc.currency, 0.0) + acc.balance
        )
        balance_details.append({
            "account_id": str(acc.id),
            "name": acc.name,
            "currency": acc.currency,
            "balance": acc.balance,
        })

    # Active recurring expenses
    active_recurring = list_recurring(session, active_only=True)
    recurring_by_currency: dict[str, float] = {}
    for r in active_recurring:
        recurring_by_currency[r["currency"]] = (
            recurring_by_currency.get(r["currency"], 0.0) + r["amount"]
        )

    # Active expected income
    active_income = list_income(session, active_only=True)
    income_by_currency: dict[str, float] = {}
    for inc in active_income:
        income_by_currency[inc["currency"]] = (
            income_by_currency.get(inc["currency"], 0.0) + inc["amount"]
        )

    # Run-rate projected variable spend (per currency)
    # Uses current month's actual spending scaled to full month
    current_month_spending = get_spending_by_category(
        start=today.replace(day=1),
        end=today,
    )
    actual_by_currency: dict[str, float] = {}
    for row in current_month_spending:
        actual_by_currency[row["currency"]] = (
            actual_by_currency.get(row["currency"], 0.0) + row["amount"]
        )

    projected_variable_spend = []
    for currency, actual in actual_by_currency.items():
        if days_elapsed > 0:
            projected = (actual / days_elapsed) * days_in_month
        else:
            projected = 0.0
        projected_variable_spend.append({
            "currency": currency,
            "projected": round(projected, 2),
            "actual_so_far": round(actual, 2),
        })

    # Forecast per currency: balance - recurring - projected_variable + income
    all_currencies = (
        set(balances_by_currency)
        | set(recurring_by_currency)
        | set(income_by_currency)
        | {r["currency"] for r in projected_variable_spend}
    )
    forecast_by_currency = []
    projected_map = {r["currency"]: r["projected"] for r in projected_variable_spend}
    for currency in sorted(all_currencies):
        balance = balances_by_currency.get(currency, 0.0)
        recurring_total = recurring_by_currency.get(currency, 0.0)
        income_total = income_by_currency.get(currency, 0.0)
        projected = projected_map.get(currency, 0.0)
        forecast = balance - recurring_total - projected + income_total
        forecast_by_currency.append({
            "currency": currency,
            "current_balance": round(balance, 2),
            "recurring_expenses": round(recurring_total, 2),
            "projected_variable_spend": round(projected, 2),
            "expected_income": round(income_total, 2),
            "forecast": round(forecast, 2),
        })

    return {
        "balances": balance_details,
        "recurring": active_recurring,
        "income": active_income,
        "projected_variable_spend": projected_variable_spend,
        "forecast_by_currency": forecast_by_currency,
    }


def _recurring_to_dict(item: RecurringItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "name": item.name,
        "amount": item.amount,
        "currency": item.currency,
        "day_of_month": item.day_of_month,
        "category": item.category,
        "active": item.active,
        "created_at": item.created_at.isoformat(),
    }


def _income_to_dict(item: ExpectedIncomeItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "name": item.name,
        "amount": item.amount,
        "currency": item.currency,
        "day_of_month": item.day_of_month,
        "active": item.active,
        "created_at": item.created_at.isoformat(),
    }
