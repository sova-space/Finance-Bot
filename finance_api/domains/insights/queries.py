"""Analytics queries over transactions and accounts."""

from calendar import monthrange
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlmodel import Session, func, or_, select

from finance_api.core.db.engine import engine
from finance_api.domains.accounts.models import Account
from finance_api.domains.forecast.models import RecurringItem
from finance_api.domains.insights.periods import (
    LAST_7D,
    LAST_30D,
    LAST_90D,
    LAST_MONTH,
    SALARY_ANCHORED,
    THIS_MONTH,
)
from finance_api.domains.rules.models import TransactionRule
from finance_api.domains.rules.queries import match_label, matches_any
from finance_api.domains.sync.models import SyncRun
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions.models import Transaction
from finance_api.domains.trips.models import Trip


def _period_dates(period: str) -> tuple[date, date]:
    today = date.today()
    if period == THIS_MONTH:
        return today.replace(day=1), today
    if period == LAST_MONTH:
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    if period == LAST_7D:
        return today - timedelta(days=7), today
    if period == LAST_30D:
        return today - timedelta(days=30), today
    if period == LAST_90D:
        return today - timedelta(days=90), today
    return today.replace(day=1), today


def _month_range(year: int, month: int) -> tuple[date, date]:
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


def _months_ago(n: int) -> tuple[int, int]:
    """Return (year, month) for n months before the current month."""
    today = date.today()
    month = today.month - n
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    return year, month


def _calendar_month_for_offset(offset: int) -> tuple[date, date]:
    """Return the full calendar month for offset months before current month."""
    year, month = _months_ago(max(0, offset))
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    return first, last


def selected_month_label(offset: int = 0) -> str:
    """Return the short Telegram button label for a selected month."""
    start, _ = _calendar_month_for_offset(offset)
    return start.strftime("%B %Y")


def _salary_anchored_start(calendar_start: date, session: Session) -> date:
    """Return earliest FOP income date in the calendar month, or calendar_start."""
    fop_ids = session.exec(select(Account.id).where(Account.is_fop == True)).all()  # noqa: E712
    if not fop_ids:
        return calendar_start
    if calendar_start.month == 12:
        month_end = date(calendar_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(calendar_start.year, calendar_start.month + 1, 1) - timedelta(
            days=1
        )
    first = session.exec(
        select(func.min(Transaction.date))
        .where(Transaction.account_id.in_(fop_ids))
        .where(Transaction.amount > 0)
        .where(Transaction.date >= calendar_start)
        .where(Transaction.date <= month_end)
    ).first()
    return first or calendar_start


def get_account_balances() -> list[dict[str, Any]]:
    """Return current balances for all visible (non-hidden) synced accounts."""
    with Session(engine) as session:
        accounts = session.exec(
            select(Account).where(Account.hidden == False)  # noqa: E712
        ).all()
        return [
            {
                "account_id": str(a.id),
                "name": a.name,
                "currency": a.currency,
                "balance": a.balance,
                "type": a.account_type,
                "is_fop": a.is_fop,
                "synced_at": a.synced_at.isoformat() if a.synced_at else None,
            }
            for a in accounts
        ]


def get_hidden_account_balances() -> list[dict[str, Any]]:
    """Return balances for hidden (skipped) accounts."""
    with Session(engine) as session:
        accounts = session.exec(
            select(Account).where(Account.hidden == True)  # noqa: E712
        ).all()
        return [
            {
                "account_id": str(a.id),
                "name": a.name,
                "currency": a.currency,
                "balance": a.balance,
                "type": a.account_type,
                "is_fop": a.is_fop,
                "synced_at": a.synced_at.isoformat() if a.synced_at else None,
            }
            for a in accounts
        ]


def get_visible_account_count() -> int:
    """Return the number of visible accounts — used for sync time estimation."""
    with Session(engine) as session:
        return session.exec(
            select(func.count(Account.id)).where(Account.hidden == False)  # noqa: E712
        ).one()


def get_spending_by_category(
    period: str = "this_month",
    account_id: UUID | None = None,
    mode: str | None = None,
    exclude_uncategorized: bool = False,
    start: date | None = None,
    end: date | None = None,
) -> list[dict[str, Any]]:
    """Return total spending grouped by category and currency for the given period.

    When ``start`` and ``end`` are both provided they override ``period`` so that
    arbitrary date ranges (e.g. trip date ranges) can be queried without defining
    a named period.

    Returns a list of dicts with keys: ``category``, ``currency``, ``amount``.
    Amounts are positive (expenses are negated).
    """
    use_explicit_range = start is not None and end is not None
    if not use_explicit_range:
        start, end = _period_dates(period)
    with Session(engine) as session:
        if not use_explicit_range and period in SALARY_ANCHORED:
            start = _salary_anchored_start(start, session)
        q = (
            select(
                Transaction.category,
                Transaction.currency,
                func.sum(Transaction.amount),
            )
            .where(Transaction.date >= start)
            .where(Transaction.date <= end)
            .where(Transaction.amount < 0)
            .where(Transaction.is_pending == False)  # noqa: E712
        )
        if account_id:
            q = q.where(Transaction.account_id == account_id)
        if mode is not None:
            q = q.where(Transaction.mode == mode)
        if exclude_uncategorized:
            q = q.where(Transaction.category.is_not(None))  # type: ignore[union-attr]
        q = q.group_by(Transaction.category, Transaction.currency)
        rows = session.exec(q).all()
        return [
            {
                "category": category or "Uncategorized",
                "currency": currency,
                "amount": round(abs(total), 2),
            }
            for category, currency, total in rows
        ]


def get_monthly_trend(
    months: int = 3,
    account_id: UUID | None = None,
    mode: str | None = None,
) -> list[dict[str, Any]]:
    """Return month-by-month income and expense totals, split by currency.

    Returns a list of dicts with keys: ``month``, ``currency``, ``income``,
    ``expenses``.  Each (month, currency) pair is a separate row so that
    multi-currency amounts are never summed across currencies.
    """
    result = []
    for i in range(months - 1, -1, -1):
        year, month = _months_ago(i)
        first, last = _month_range(year, month)

        def _sums_by_currency(
            session: Session,
            start: date,
            end: date,
            condition: Any,
        ) -> dict[str, float]:
            base = (
                select(Transaction.currency, func.sum(Transaction.amount))
                .where(Transaction.date >= start)
                .where(Transaction.date <= end)
                .where(Transaction.is_pending == False)  # noqa: E712
                .where(condition)
                .group_by(Transaction.currency)
            )
            if account_id:
                base = base.where(Transaction.account_id == account_id)
            if mode is not None:
                base = base.where(Transaction.mode == mode)
            return {currency: total for currency, total in session.exec(base).all()}

        with Session(engine) as session:
            start_first = _salary_anchored_start(first, session) if i == 0 else first
            income_by_cur = _sums_by_currency(
                session, start_first, last, Transaction.amount > 0
            )
            expenses_by_cur = _sums_by_currency(
                session, start_first, last, Transaction.amount < 0
            )

        all_currencies = set(income_by_cur) | set(expenses_by_cur)
        month_label = first.strftime("%b %Y")
        for currency in sorted(all_currencies):
            result.append({
                "month": month_label,
                "currency": currency,
                "income": round(income_by_cur.get(currency, 0.0), 2),
                "expenses": round(abs(expenses_by_cur.get(currency, 0.0)), 2),
            })
    return result


def get_recent_transactions(
    limit: int = 20,
    period: str | None = None,
    account_id: UUID | None = None,
    mode: str | None = None,
) -> list[dict[str, Any]]:
    """Return recent transactions, optionally filtered by period, account, and mode."""
    with Session(engine) as session:
        q = (
            select(Transaction)
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        if period:
            start, end = _period_dates(period)
            if period in SALARY_ANCHORED:
                start = _salary_anchored_start(start, session)
            q = q.where(Transaction.date >= start).where(Transaction.date <= end)
        if account_id:
            q = q.where(Transaction.account_id == account_id)
        if mode is not None:
            q = q.where(Transaction.mode == mode)
        txs = session.exec(q).all()
        return [
            {
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "currency": t.currency,
                "category": t.category,
                "mode": t.mode,
                "is_pending": t.is_pending,
            }
            for t in txs
        ]


def get_sync_health() -> dict[str, Any]:
    """Return the status of the most recent sync run."""
    with Session(engine) as session:
        last_run = session.exec(
            select(SyncRun).order_by(SyncRun.started_at.desc()).limit(1)  # type: ignore[attr-defined]
        ).first()
        if not last_run:
            return {"status": "never_synced"}
        return {
            "status": last_run.status,
            "started_at": (
                last_run.started_at.isoformat() if last_run.started_at else None
            ),
            "completed_at": (
                last_run.completed_at.isoformat() if last_run.completed_at else None
            ),
            "tx_imported": last_run.tx_imported,
            "error": last_run.error,
        }


def get_subscriptions(offset: int = 0) -> dict[str, Any]:
    """Return subscription summary for the selected calendar month."""
    start, end = _calendar_month_for_offset(offset)
    lookback_90 = end - timedelta(days=90)
    lookback_400 = end - timedelta(days=400)

    with Session(engine) as session:
        # All subscription transactions in last 90 days
        recent_rows = session.exec(
            select(
                Transaction.description,
                func.count(Transaction.id),
                func.avg(func.abs(Transaction.amount)),
                func.max(Transaction.date),
            )
            .where(Transaction.category == cat.SUBSCRIPTIONS)
            .where(Transaction.amount < 0)
            .where(Transaction.date >= start)
            .where(Transaction.date <= end)
            .where(Transaction.is_pending == False)  # noqa: E712
            .group_by(Transaction.description)
            .order_by(func.avg(func.abs(Transaction.amount)).desc())
        ).all()

        # For each description: check how many distinct calendar months it appeared in
        # and whether it existed ~1 year ago (yearly detection)
        def _monthly_months(desc: str) -> int:
            trunc = func.date_trunc("month", Transaction.date).label("mo")
            month_rows = session.exec(
                select(trunc)
                .where(Transaction.category == cat.SUBSCRIPTIONS)
                .where(Transaction.description == desc)
                .where(Transaction.amount < 0)
                .where(Transaction.date >= lookback_90)
                .group_by(trunc)
            ).all()
            return len(month_rows)

        def _has_yearly_history(desc: str) -> bool:
            old = session.exec(
                select(func.count(Transaction.id))
                .where(Transaction.category == cat.SUBSCRIPTIONS)
                .where(Transaction.description == desc)
                .where(Transaction.amount < 0)
                .where(Transaction.date >= lookback_400)
                .where(Transaction.date < lookback_90)
            ).one()
            return (old or 0) >= 1

        recurring = session.exec(select(RecurringItem)).all()
        yearly_in_recurring = {
            r.name.lower()
            for r in recurring
            if r.category == cat.SUBSCRIPTIONS and r.day_of_month is not None
        }

        monthly, yearly, one_time = [], [], []
        for desc, count, avg_amt, last_date in recent_rows:
            amt = round(float(avg_amt))
            months_seen = _monthly_months(desc)
            desc_lower = desc.lower()
            is_yearly_recurring = any(k in desc_lower for k in yearly_in_recurring)
            has_old = _has_yearly_history(desc)

            item = {
                "name": desc,
                "amount": amt,
                "last_date": last_date.isoformat() if last_date else None,
            }

            if is_yearly_recurring or (count == 1 and has_old):
                yearly.append({**item, "yearly": amt, "monthly_equiv": round(amt / 12)})
            elif months_seen >= 2:
                monthly.append({**item, "yearly_equiv": amt * 12})
            elif count == 1 and not has_old:
                one_time.append(item)
            else:
                monthly.append({**item, "yearly_equiv": amt * 12})

    monthly.sort(key=lambda x: x["amount"], reverse=True)
    yearly.sort(key=lambda x: x["amount"], reverse=True)

    monthly_total = sum(s["amount"] for s in monthly)
    yearly_monthly_equiv = sum(s["monthly_equiv"] for s in yearly)
    return {
        "monthly": monthly,
        "yearly": yearly,
        "one_time": one_time,
        "monthly_total": monthly_total,
        "yearly_monthly_equiv": yearly_monthly_equiv,
        "total_per_month": monthly_total + yearly_monthly_equiv,
        "total_per_year": monthly_total * 12 + sum(s["yearly"] for s in yearly),
    }


def _selected_rules(session: Session, rule_type: str) -> list[tuple[str, str]]:
    rows = session.exec(
        select(TransactionRule.pattern, TransactionRule.label).where(
            TransactionRule.rule_type == rule_type
        )
    ).all()
    return list(rows)


def get_spending_summary(offset: int = 0) -> dict[str, Any]:
    """Return UAH spending by category for the selected calendar month."""
    start, end = _calendar_month_for_offset(offset)
    with Session(engine) as session:
        personal_ids = session.exec(
            select(Account.id).where(Account.is_fop == False)  # noqa: E712
        ).all()
        summary_rows = session.exec(
            select(
                Transaction.category,
                Transaction.currency,
                func.sum(Transaction.amount),
            )
            .where(Transaction.account_id.in_(personal_ids))
            .where(Transaction.date >= start)
            .where(Transaction.date <= end)
            .where(Transaction.amount < 0)
            .where(Transaction.is_pending == False)  # noqa: E712
            .group_by(Transaction.category, Transaction.currency)
        ).all()
        rows = [
            {
                "category": category or "Uncategorized",
                "currency": currency,
                "amount": round(abs(total), 2),
            }
            for category, currency, total in summary_rows
        ]

        # Per-category transaction details for drill-down (all currencies)
        detail_rows = session.exec(
            select(
                Transaction.category,
                Transaction.description,
                Transaction.amount,
                Transaction.date,
                Transaction.currency,
            )
            .where(
                Transaction.account_id.in_(
                    select(Account.id).where(Account.is_fop == False)  # noqa: E712
                )
            )
            .where(Transaction.amount < 0)
            .where(Transaction.date >= start)
            .where(Transaction.date <= end)
            .where(Transaction.is_pending == False)  # noqa: E712
            .where(
                or_(
                    Transaction.category.is_(None),
                    Transaction.category.notin_(  # type: ignore[union-attr]
                        ["Couple Transfer", "Cashback"]
                    ),
                )
            )
            .order_by(Transaction.category, Transaction.amount)
        ).all()

        # Rules for label lookup (auto_category)
        auto_rules = _selected_rules(session, "auto_category")

        # Trips overlapping the period for Travel label lookup
        trips = session.exec(
            select(Trip).where(Trip.start_date <= end).where(Trip.end_date >= start)
        ).all()

        def _label(cat_name: str, desc: str, tx_date: date) -> str:
            """Return a user-friendly group label for a transaction."""
            matched = match_label(desc, auto_rules)
            if matched:
                return matched
            if cat_name == cat.TRAVEL:
                for trip in trips:
                    if trip.start_date <= tx_date <= trip.end_date:
                        return trip.name
            return desc

        by_cat: dict[str, list[dict[str, Any]]] = {}
        for cat_name, desc, amt, dt, currency in detail_rows:
            category = cat_name or "Uncategorized"
            by_cat.setdefault(category, []).append({
                "description": desc,
                "label": _label(category, desc, dt),
                "amount": round(abs(amt), 2),
                "currency": currency,
                "date": dt.isoformat(),
            })

    return {
        "rows": rows,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "details": by_cat,
        "offset": offset,
    }


def get_income_summary(offset: int = 0) -> dict[str, Any]:
    """Return income for the selected calendar month."""
    start, end = _calendar_month_for_offset(offset)
    with Session(engine) as session:
        # FOP USD: external salary only. FOP UAH: internal transfers.
        fop_usd_ids = session.exec(
            select(Account.id).where(
                Account.is_fop == True,  # noqa: E712
                Account.currency == "USD",
            )
        ).all()
        personal_ids = session.exec(
            select(Account.id).where(Account.is_fop == False)  # noqa: E712
        ).all()

        not_cashback = or_(
            Transaction.category.is_(None),
            Transaction.category != cat.CASHBACK,
        )

        def _fop_income_txns(acc_ids: list) -> list[dict[str, Any]]:
            if not acc_ids:
                return []
            rows = session.exec(
                select(Transaction)
                .where(Transaction.account_id.in_(acc_ids))
                .where(Transaction.amount > 0)
                .where(not_cashback)
                .where(Transaction.date >= start)
                .where(Transaction.date <= end)
                .where(Transaction.is_pending == False)  # noqa: E712
                .order_by(Transaction.date)
            ).all()
            return [
                {
                    "date": t.date.isoformat(),
                    "amount": t.amount,
                    "currency": t.currency,
                    "description": t.description,
                }
                for t in rows
            ]

        def _personal_income_txns(acc_ids: list) -> list[dict[str, Any]]:
            if not acc_ids:
                return []
            income_rules = _selected_rules(session, "personal_income")
            if not income_rules:
                return []
            income_patterns = [p for p, _ in income_rules]
            rows = session.exec(
                select(Transaction)
                .where(Transaction.account_id.in_(acc_ids))
                .where(Transaction.amount > 0)
                .where(not_cashback)
                .where(Transaction.date >= start)
                .where(Transaction.date <= end)
                .where(Transaction.is_pending == False)  # noqa: E712
                .order_by(Transaction.date)
            ).all()
            return [
                {
                    "date": t.date.isoformat(),
                    "amount": t.amount,
                    "currency": t.currency,
                    "description": match_label(t.description, income_rules)
                    or t.description,
                }
                for t in rows
                if matches_any(t.description, income_patterns)
            ]

        fop_txns = _fop_income_txns(fop_usd_ids)
        personal_txns = _personal_income_txns(personal_ids)

        def _totals(
            txns: list[dict[str, Any]],
        ) -> dict[str, int]:
            totals: dict[str, int] = {}
            for t in txns:
                totals[t["currency"]] = totals.get(t["currency"], 0) + t["amount"]
            return totals

        fop = _totals(fop_txns)
        personal = _totals(personal_txns)

        # Current balance per currency across personal accounts
        balance_rows = session.exec(
            select(Account.currency, func.sum(Account.balance))
            .where(Account.id.in_(personal_ids))
            .where(Account.hidden == False)  # noqa: E712
            .group_by(Account.currency)
        ).all()
        balances = {c: round(v) for c, v in balance_rows if v}

        # USD→UAH rate: pick highest exchange_rate value among FOP conversions
        # (rates > 1 are UAH/USD; rates < 1 are the inverse — skip those)
        fop_all_ids = session.exec(
            select(Account.id).where(Account.is_fop == True)  # noqa: E712
        ).all()
        rate_rows = session.exec(
            select(Transaction.extra)
            .where(Transaction.account_id.in_(fop_all_ids))
            .where(Transaction.extra.isnot(None))  # type: ignore[union-attr]
            .where(Transaction.date >= start)
            .where(Transaction.date <= end)
        ).all()
        usd_uah_rate: float | None = None
        for row in rate_rows:
            try:
                er = float(row["exchange_rate"])  # type: ignore[index]
                if er > 1 and (usd_uah_rate is None or er > usd_uah_rate):
                    usd_uah_rate = er
            except (KeyError, TypeError, ValueError):
                pass

        # Period start = earliest actual salary transaction date
        all_salary_dates = [
            date.fromisoformat(t["date"]) for t in fop_txns + personal_txns
        ]
        salary_start = min(all_salary_dates) if all_salary_dates else start

        all_currencies = sorted(set(fop) | set(personal))
        return {
            "period": date.today().strftime("%b %Y"),
            "period_start": salary_start.isoformat(),
            "period_end": end.isoformat(),
            "balances": balances,
            "usd_uah_rate": usd_uah_rate,
            "by_currency": {
                c: {
                    "fop": fop.get(c, 0),
                    "personal": personal.get(c, 0),
                    "fop_txns": [t for t in fop_txns if t["currency"] == c],
                    "personal_txns": [t for t in personal_txns if t["currency"] == c],
                }
                for c in all_currencies
            },
        }


_BIG_INCOME_SALARY_THRESHOLD = 20_000


def _is_salary_like(tx: Transaction, account: Account) -> bool:
    """Return True for transactions that should start a salary-cycle month."""
    if tx.amount <= 0 or tx.is_pending or tx.category == cat.CASHBACK:
        return False
    return bool(
        account.is_fop
        or tx.category == cat.INCOME
        or tx.amount >= _BIG_INCOME_SALARY_THRESHOLD
    )


_SALARY_CLUSTER_DAYS = 7


def _salary_cycle_dates(session: Session) -> list[date]:
    rows = session.exec(
        select(Transaction, Account)
        .join(Account, Transaction.account_id == Account.id)
        .where(Transaction.amount > 0)
        .where(Transaction.is_pending == False)  # noqa: E712
        .where(Transaction.date <= date.today())
        .order_by(Transaction.date)
    ).all()
    raw_dates = sorted({
        tx.date for tx, account in rows if _is_salary_like(tx, account)
    })
    if not raw_dates:
        return []

    # Salary often arrives as a cluster (FOP income, conversion, personal top-up).
    # Treat close income dates as one cycle so navigation doesn't split one month
    # into several fake "months".
    clusters: list[list[date]] = [[raw_dates[0]]]
    for dt in raw_dates[1:]:
        if (dt - clusters[-1][-1]).days <= _SALARY_CLUSTER_DAYS:
            clusters[-1].append(dt)
        else:
            clusters.append([dt])
    return sorted((cluster[0] for cluster in clusters), reverse=True)


def _personal_balances_as_of(session: Session, end: date) -> dict[str, int]:
    accounts = session.exec(
        select(Account).where(
            Account.hidden == False,  # noqa: E712
            or_(Account.is_fop == False, Account.currency == "USD"),  # noqa: E712
        )
    ).all()
    if not accounts:
        return {}

    balances: dict[str, float] = {}
    for account in accounts:
        after = session.exec(
            select(func.sum(Transaction.amount))
            .where(Transaction.account_id == account.id)
            .where(Transaction.date > end)
            .where(Transaction.is_pending == False)  # noqa: E712
        ).one()
        balances[account.currency] = balances.get(account.currency, 0.0) + (
            account.balance - (after or 0.0)
        )
    return {currency: round(value) for currency, value in balances.items() if value}


def _income_summary_between(start: date, end: date) -> dict[str, Any]:
    with Session(engine) as session:
        fop_usd_ids = session.exec(
            select(Account.id).where(
                Account.is_fop == True,  # noqa: E712
                Account.currency == "USD",
            )
        ).all()
        personal_ids = session.exec(
            select(Account.id).where(Account.is_fop == False)  # noqa: E712
        ).all()
        income_rules = _selected_rules(session, "personal_income")
        income_patterns = [pattern for pattern, _label in income_rules]
        not_cashback = or_(
            Transaction.category.is_(None), Transaction.category != cat.CASHBACK
        )

        fop_rows = session.exec(
            select(Transaction)
            .where(Transaction.account_id.in_(fop_usd_ids))
            .where(Transaction.amount > 0)
            .where(Transaction.date >= start)
            .where(Transaction.date <= end)
            .where(Transaction.is_pending == False)  # noqa: E712
            .where(not_cashback)
            .order_by(Transaction.date)
        ).all()
        personal_rows = session.exec(
            select(Transaction)
            .where(Transaction.account_id.in_(personal_ids))
            .where(Transaction.amount > 0)
            .where(Transaction.date >= start)
            .where(Transaction.date <= end)
            .where(Transaction.is_pending == False)  # noqa: E712
            .where(not_cashback)
            .order_by(Transaction.date)
        ).all()
        rate_rows = session.exec(
            select(Transaction.extra)
            .where(Transaction.date >= start)
            .where(Transaction.date <= end)
            .where(Transaction.extra.isnot(None))  # type: ignore[union-attr]
        ).all()
        balance_rows = _personal_balances_as_of(session, end)

    fop_txns = [
        {
            "date": tx.date.isoformat(),
            "amount": tx.amount,
            "currency": tx.currency,
            "description": tx.description,
        }
        for tx in fop_rows
    ]
    personal_txns = [
        {
            "date": tx.date.isoformat(),
            "amount": tx.amount,
            "currency": tx.currency,
            "description": match_label(tx.description, income_rules) or tx.description,
        }
        for tx in personal_rows
        if matches_any(tx.description, income_patterns)
    ]

    usd_uah_rate: float | None = None
    for row in rate_rows:
        try:
            er = float(row["exchange_rate"])  # type: ignore[index]
            if er > 1 and (usd_uah_rate is None or er > usd_uah_rate):
                usd_uah_rate = er
        except (KeyError, TypeError, ValueError):
            pass

    def _totals(txns: list[dict[str, Any]]) -> dict[str, float]:
        totals: dict[str, float] = {}
        for tx in txns:
            totals[tx["currency"]] = totals.get(tx["currency"], 0) + tx["amount"]
        return totals

    fop = _totals(fop_txns)
    personal = _totals(personal_txns)
    currencies = sorted(set(fop) | set(personal))
    return {
        "period": start.strftime("%b %Y"),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "balances": balance_rows,
        "usd_uah_rate": usd_uah_rate,
        "by_currency": {
            currency: {
                "fop": fop.get(currency, 0),
                "personal": personal.get(currency, 0),
                "fop_txns": [tx for tx in fop_txns if tx["currency"] == currency],
                "personal_txns": [
                    tx for tx in personal_txns if tx["currency"] == currency
                ],
            }
            for currency in currencies
        },
    }


def _spending_summary_between(start: date, end: date) -> dict[str, Any]:
    return {
        "rows": get_spending_by_category(start=start, end=end),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "details": {},
    }


def get_month_cycle_summary(offset: int = 0) -> dict[str, Any]:
    """Return one selected calendar month summary.

    offset=0 is the current calendar month. offset=1 is the previous month.
    """
    offset = max(0, offset)
    start, end = _calendar_month_for_offset(offset)
    return {
        "offset": offset,
        "has_previous": True,
        "has_next": offset > 0,
        "income": _income_summary_between(start, end),
        "spending": get_spending_summary(offset),
    }
