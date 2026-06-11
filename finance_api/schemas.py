"""Response schemas for all API endpoints."""

from pydantic import BaseModel, Field


class AccountBalance(BaseModel):
    """Current balance for a single Monobank account."""

    account_id: str = Field(
        description="Internal UUID — pass as ?account_id= to scope transaction queries"
    )
    name: str = Field(
        description="Human-readable account name, e.g. 'Monobank Black UAH'"
    )
    currency: str = Field(description="ISO 4217 currency code, e.g. 'UAH'")
    balance: float = Field(
        description="Current balance in major units (kopecks converted to hryvnias)"
    )
    type: str = Field(
        description=(
            "Monobank account type: black | white | fop | platinum | iron | yellow"
        )
    )
    is_fop: bool = Field(
        default=False,
        description="True if account receives salary; used to anchor month start",
    )
    synced_at: str | None = Field(
        default=None,
        description="ISO timestamp of the last successful sync for this account",
    )


class TransactionItem(BaseModel):
    """A single bank transaction."""

    date: str = Field(description="Transaction date, ISO format YYYY-MM-DD")
    description: str = Field(
        description="Merchant or transfer description from Monobank"
    )
    amount: float = Field(
        description=(
            "Amount in major currency units. Negative = expense, positive = income"
        )
    )
    currency: str = Field(description="ISO 4217 currency code")
    category: str | None = Field(
        default=None,
        description="Spending category inferred from MCC code",
    )
    mode: str | None = Field(
        default=None,
        description="'solo' (personal), 'couple' (shared), or None (income/cashback)",
    )
    is_pending: bool = Field(
        default=False,
        description="True if the transaction has not yet cleared (hold/authorisation)",
    )


class SpendingRow(BaseModel):
    """Spending total for a single category and currency."""

    category: str = Field(description="Spending category, e.g. 'Food & Drink'")
    currency: str = Field(description="ISO 4217 currency code, e.g. 'UAH'")
    amount: float = Field(
        description="Total amount spent (positive value, expenses are negated)"
    )


class MonthlyTrend(BaseModel):
    """Income and expense totals for a single calendar month and currency."""

    month: str = Field(description="Month label, e.g. 'May 2026'")
    currency: str = Field(description="ISO 4217 currency code, e.g. 'UAH'")
    income: float = Field(
        description="Total income for this month (positive transactions)"
    )
    expenses: float = Field(
        description=(
            "Total expenses for this month (absolute value of negative transactions)"
        )
    )


class SyncStatus(BaseModel):
    """Status of the most recent Monobank sync run."""

    status: str = Field(
        description="One of: never_synced | running | completed | failed"
    )
    started_at: str | None = Field(
        default=None,
        description="ISO timestamp when sync started",
    )
    completed_at: str | None = Field(
        default=None,
        description="ISO timestamp when sync finished",
    )
    tx_imported: int = Field(
        default=0,
        description="Number of new transactions imported in this run",
    )
    error: str | None = Field(
        default=None,
        description="Error message if status is 'failed'",
    )


class SyncTriggered(BaseModel):
    """Confirmation that a sync has been triggered."""

    status: str = Field(description="Always 'started' — sync runs in the background")


class HealthResponse(BaseModel):
    """Service health status."""

    status: str = Field(description="Always 'ok' if the API is reachable")
    sync: SyncStatus = Field(description="Status of the last Monobank sync")


class BudgetItem(BaseModel):
    """A single category budget with current-month spending."""

    category: str = Field(description="Canonical category name, e.g. 'Food & Drink'")
    monthly_limit: float = Field(description="Spending limit for the month")
    currency: str = Field(description="Currency code the limit is expressed in")
    spent: float = Field(description="Amount spent this month in this category")
    remaining: float = Field(
        description="monthly_limit minus spent (negative means over budget)"
    )
    exceeded: bool = Field(description="True when spent > monthly_limit")


class BudgetSet(BaseModel):
    """Confirmation of a created or updated budget."""

    category: str = Field(description="Category the limit applies to")
    monthly_limit: float = Field(description="New monthly spending limit")
    currency: str = Field(description="Currency code")
