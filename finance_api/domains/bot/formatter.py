"""Format Finance API data as Telegram HTML messages."""

from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

from finance_api.bot.telegram_fmt import bold, code, italic, pre
from finance_api.domains.transactions import categories as cat

CATEGORY_EMOJI: dict[str, str] = {
    cat.FOOD_AND_DRINK: "🍔",
    cat.GROCERIES: "🛒",
    cat.TRANSPORTATION: "🚇",
    cat.HEALTHCARE: "💊",
    cat.SHOPPING: "🛍️",
    cat.ENTERTAINMENT: "🎮",
    cat.TRAVEL: "✈️",
    cat.SUBSCRIPTIONS: "📱",
    cat.UTILITIES: "⚡",
    cat.ATM_CASH: "🏧",
    cat.FINANCE: "💳",
    cat.EDUCATION: "🎓",
    cat.PETS: "🐾",
    cat.CASHBACK: "💰",
    cat.INCOME: "💰",
    cat.COUPLE_TRANSFER: "💸",
    cat.PARTNER: "💑",
}

# Currencies where the symbol goes before the amount (e.g. $1,234)
_PREFIX_CURRENCIES = {"USD", "EUR", "GBP"}
CURRENCY_SYMBOL: dict[str, str] = {"UAH": "₴", "USD": "$", "EUR": "€", "GBP": "£"}
_BASE_CURRENCY = "UAH"
_FOP_CURRENCY = "USD"

_PERIOD_LABEL: dict[str, str] = {
    "this_month": date.today().strftime("%B %Y"),
    "last_month": "last month",
    "last_7d": "last 7 days",
    "last_30d": "last 30 days",
    "last_90d": "last 90 days",
}


def _emoji(category: str) -> str:
    return CATEGORY_EMOJI.get(category, "📦")


def _sym(currency: str) -> str:
    return CURRENCY_SYMBOL.get(currency, currency)


def _fmt_amount(amount: float, currency: str) -> str:
    """Format an amount with the correct currency symbol position and precision."""
    sym = _sym(currency)
    # Use integers for whole amounts, two decimals otherwise
    formatted = f"{amount:,.0f}" if amount == int(amount) else f"{amount:,.2f}"
    if currency in _PREFIX_CURRENCIES:
        return f"{sym}{formatted}"
    return f"{formatted} {sym}"


def _fmt_ago(iso: str | None) -> str:
    """Return a human-readable 'N min ago' / 'N hours ago' string."""
    if not iso:
        return "never"
    dt = datetime.fromisoformat(iso)
    # Normalise both sides to UTC-aware for a safe subtraction.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - dt
    total_minutes = int(delta.total_seconds() // 60)
    if total_minutes < 1:
        return "just now"
    if total_minutes < 60:
        return f"{total_minutes} min ago"
    hours = total_minutes // 60
    return f"{hours} hour{'s' if hours != 1 else ''} ago"


def _short_name(name: str, currency: str) -> str:
    """Strip 'Monobank ' prefix and trailing currency code from account name."""
    return name.replace("Monobank ", "").replace(f" {currency}", "").strip()


_CURRENCY_FLAG: dict[str, str] = {
    "UAH": "🇺🇦",
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "GBP": "🇬🇧",
}


def _cycle_dates(month: dict[str, Any] | None) -> tuple[date, date] | None:
    if not month:
        return None
    spending = month.get("spending", month)
    start_raw = spending.get("period_start")
    end_raw = spending.get("period_end")
    if not start_raw or not end_raw:
        return None
    return date.fromisoformat(start_raw), date.fromisoformat(end_raw)


def _cycle_label(start: date) -> str:
    return start.strftime("%B")


def _cycle_range(start: date, end: date) -> str:
    if start.month == end.month:
        return f"{start.strftime('%-d')}-{end.strftime('%-d %b')}"
    return f"{start.strftime('%-d %b')}-{end.strftime('%-d %b')}"


def _format_cycle_line(month: dict[str, Any] | None) -> str:
    dates = _cycle_dates(month)
    if not dates:
        return ""
    start, end = dates
    label = bold(f"Month · {_cycle_label(start)}")
    range_label = italic(_cycle_range(start, end))
    return f"📅 {label} · {range_label}"


def format_balance(
    accounts: list[dict[str, Any]], month: dict[str, Any] | None = None
) -> str:
    """Format balances: currency totals visible, per-account details expandable."""
    if not accounts:
        return "No accounts synced yet. Run /sync first."

    by_currency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in accounts:
        by_currency[a["currency"]].append(a)

    group_totals: dict[str, float] = {
        currency: round(sum(a["balance"] for a in group))
        for currency, group in by_currency.items()
    }

    # Totals section — always visible
    total_lines: list[str] = []
    for currency, _group in by_currency.items():
        flag = _CURRENCY_FLAG.get(currency, "💱")
        total_str = _fmt_amount(group_totals[currency], currency)
        total_lines.append(f"{flag} {currency}  {bold(total_str)}")

    latest_sync = max(
        (a["synced_at"] for a in accounts if a.get("synced_at")),
        default=None,
    )
    cycle_line = _format_cycle_line(month)
    cycle_block = f"\n{cycle_line}\n" if cycle_line else "\n"
    income_block = ""
    if month and month.get("income"):
        income_text = format_income_summary(month["income"])
        if income_text:
            income_block = f"\n\n{income_text}"
    return (
        f"💳 {bold('Mono')}\n"
        + cycle_block
        + "\n".join(total_lines)
        + income_block
        + f"\n\n🕐 {_fmt_ago(latest_sync)}"
    )


def _fmt_income_period(summary: dict[str, Any]) -> str:
    start_raw = summary.get("period_start")
    if not start_raw:
        return summary.get("period", "")
    return date.fromisoformat(start_raw).strftime("%b %-d")


def format_income_summary(summary: dict[str, Any]) -> str:
    """Format income: earned totals visible, source/spending details expandable."""
    by_cur = summary.get("by_currency", {})
    if not by_cur:
        return ""

    # Validate there's something to show
    has_data = any(v["fop"] or v["personal"] for v in by_cur.values())
    if not has_data:
        return ""

    # Collect all salary transactions and all spending, grouped by currency
    all_txns: list[tuple[str, str, dict[str, Any]]] = []
    for currency, v in by_cur.items():
        for t in v.get("fop_txns", []):
            all_txns.append(("FOP", currency, t))
        for t in v.get("personal_txns", []):
            all_txns.append(("Personal", currency, t))
    all_txns.sort(key=lambda x: x[2]["date"])

    if not all_txns:
        return ""

    rate: float | None = summary.get("usd_uah_rate")

    # Income totals per currency
    income_by_cur: dict[str, float] = {}
    for _source, currency, t in all_txns:
        income_by_cur[currency] = income_by_cur.get(currency, 0) + t["amount"]

    balances = summary.get("balances", {})
    has_both = (
        rate and _FOP_CURRENCY in income_by_cur and _BASE_CURRENCY in income_by_cur
    )

    if has_both:
        # Two-currency table: source | UAH | USD
        rows: list[tuple[str, float, float]] = []
        for _source, currency, t in all_txns:
            dt = date.fromisoformat(t["date"])
            sender = t["description"].removeprefix("Від: ").strip()
            label = f"{sender} · {dt.strftime('%b %-d')}"
            uah = t["amount"] * rate if currency == _FOP_CURRENCY else t["amount"]  # type: ignore[operator]
            usd = t["amount"] if currency == _FOP_CURRENCY else t["amount"] / rate  # type: ignore[operator]
            rows.append((label, uah, usd))

        base_total = round(
            income_by_cur.get(_BASE_CURRENCY, 0)
            + income_by_cur.get(_FOP_CURRENCY, 0) * rate  # type: ignore[operator]
        )
        usd_total = round(
            income_by_cur.get(_FOP_CURRENCY, 0)
            + income_by_cur.get(_BASE_CURRENCY, 0) / rate  # type: ignore[operator]
        )

        # Use plain numbers (no currency symbols) in cells — symbols in headers only
        def _num(v: float) -> str:
            return f"{round(v):,}"

        uah_hdr = _sym(_BASE_CURRENCY)
        usd_hdr = _sym(_FOP_CURRENCY)

        src_hdr = "Source"
        label_w = max(max(len(r[0]) for r in rows), len(src_hdr), len("Total"))
        uah_w = max(
            max(len(_num(r[1])) for r in rows),
            len(_num(base_total)),
            len(uah_hdr),
        )
        usd_w = max(
            max(len(_num(r[2])) for r in rows),
            len(_num(usd_total)),
            len(usd_hdr),
        )
        div = "─" * (label_w + 2 + uah_w + 2 + usd_w)

        table_lines: list[str] = [
            f"{src_hdr:<{label_w}}  {uah_hdr:>{uah_w}}  {usd_hdr:>{usd_w}}"
        ]
        for label, uah, usd in rows:
            table_lines.append(
                f"{label:<{label_w}}  {_num(uah):>{uah_w}}  {_num(usd):>{usd_w}}"
            )
        table_lines.append(div)
        table_lines.append(
            f"{'Total':<{label_w}}"
            f"  {_num(base_total):>{uah_w}}"
            f"  {_num(usd_total):>{usd_w}}"
        )
        fop_sym = _sym(_FOP_CURRENCY)
        base_sym = _sym(_BASE_CURRENCY)
        rate_note = f"  {fop_sym}1 = {rate:,.2f} {base_sym}"  # type: ignore[operator]
        received_block = pre("\n".join(table_lines)) + f"\n{italic(rate_note)}"
    else:
        received_lines: list[str] = []
        for source, currency, t in all_txns:
            dt = date.fromisoformat(t["date"])
            sender = t["description"].removeprefix("Від: ").strip()
            flag = _CURRENCY_FLAG.get(currency, "💱")
            label = f"{flag} {source} · {dt.strftime('%b %-d')} · {sender}"
            received_lines.append(
                f"  {label}  {bold(_fmt_amount(t['amount'], currency))}"
            )
        received_block = "\n".join(received_lines)

    # Balance: "X of TOTAL · spent Y%", skip negligible balances
    NEGLIGIBLE = {"UAH": 50, "USD": 5, "EUR": 5, "GBP": 5}
    balance_rows: list[tuple[str, str, str]] = []
    for currency in sorted(income_by_cur):
        bal = balances.get(currency, 0)
        if bal < NEGLIGIBLE.get(currency, 5):
            continue
        if currency == _BASE_CURRENCY and rate and _FOP_CURRENCY in income_by_cur:
            received = (
                income_by_cur.get(_BASE_CURRENCY, 0)
                + income_by_cur.get(_FOP_CURRENCY, 0) * rate
            )
        else:
            received = income_by_cur[currency]
        flag = _CURRENCY_FLAG.get(currency, "💱")
        pct = round((received - bal) / received * 100) if received else 0
        balance_rows.append((
            flag,
            _fmt_amount(round(bal), currency),
            f"of {_fmt_amount(round(received), currency)} · spent {pct}%",
        ))

    body = f"💰 {bold('Income')}\n{received_block}"
    if balance_rows:
        bal_w = max(len(row[1]) for row in balance_rows)
        balance_table = "\n".join(
            f"{flag} {balance:>{bal_w}}  {note}" for flag, balance, note in balance_rows
        )
        body += f"\n\n💳 {bold('Balance now')}\n" + pre(balance_table)

    return body


def format_month_report(income: dict[str, Any], spending: dict[str, Any]) -> str:
    """Format one salary-to-salary month management summary."""
    dates = _cycle_dates(spending) or _cycle_dates(income)
    if dates:
        start, end = dates
        label = _cycle_label(start)
        range_label = _cycle_range(start, end)
    else:
        label = _fmt_income_period(income) or "current"
        range_label = "salary to salary"

    income_text = format_income_summary(income) or "No income data yet."
    spending_text = format_spending_summary(spending) or "No spending recorded yet."
    return (
        f"📅 {bold(f'Month · {label}')}\n"
        f"{italic(range_label)}\n\n"
        f"{bold('Income')}\n{income_text}\n\n"
        f"{bold('Spending')}\n{spending_text}"
    )


def format_spending_summary(data: dict[str, Any]) -> str:
    """Format salary-cycle UAH spending by category."""
    EXCLUDED = {cat.COUPLE_TRANSFER, cat.CASHBACK}
    rows = [
        r
        for r in data.get("rows", [])
        if r["currency"] == "UAH" and r["category"] not in EXCLUDED
    ]
    if not rows:
        return ""

    rows.sort(key=lambda r: r["amount"], reverse=True)
    total = sum(r["amount"] for r in rows)

    start = date.fromisoformat(data["period_start"])
    end = date.fromisoformat(data["period_end"])
    if start.month == end.month:
        period_label = f"{start.strftime('%-d')}-{end.strftime('%-d %b')}"
    else:
        period_label = f"{start.strftime('%-d %b')}-{end.strftime('%-d %b')}"

    name_w = max(len(r["category"]) for r in rows)
    amt_w = max(max(len(f"{r['amount']:,.0f}") for r in rows), len("Total"))

    # Summary table — no emoji inside pre so columns align perfectly
    summary_lines: list[str] = []
    for r in rows:
        pct = round(r["amount"] / total * 100) if total else 0
        amt_str = f"{r['amount']:,.0f}"
        summary_lines.append(
            f"{r['category']:<{name_w}}  {amt_str:>{amt_w}}  {pct:>3}%"
        )
    summary_lines.append("─" * (name_w + 2 + amt_w + 5))
    summary_lines.append(f"{'Total':<{name_w}}  {total:>{amt_w},.0f}")

    header = f"📊 {bold(f'Spending — {period_label}')}"
    return header + "\n\n" + pre("\n".join(summary_lines))


_MAX_DETAIL_ROWS = 50


def format_spending_category(data: dict[str, Any], category: str) -> str:
    """Format detail view for a single spending category."""
    EXCLUDED = {cat.COUPLE_TRANSFER, cat.CASHBACK}
    rows = [
        r
        for r in data.get("rows", [])
        if r["currency"] == "UAH" and r["category"] not in EXCLUDED
    ]
    total_all = sum(r["amount"] for r in rows)
    cat_row = next((r for r in rows if r["category"] == category), None)
    if not cat_row:
        return f"No data for {category}."

    em = _emoji(category)
    pct = round(cat_row["amount"] / total_all * 100) if total_all else 0
    txns = sorted(
        data.get("details", {}).get(category, []),
        key=lambda t: t["amount"],
        reverse=True,
    )

    # Group by label only when label differs from description (real label exists)
    groups: dict[str, list[dict[str, Any]]] = {}
    for t in txns:
        lbl = t.get("label", t["description"])
        groups.setdefault(lbl, []).append(t)

    has_real_labels = any(
        lbl != group_txns[0]["description"] for lbl, group_txns in groups.items()
    )

    parts: list[str] = []

    if has_real_labels:
        for group_label, group_txns in sorted(
            groups.items(),
            key=lambda x: sum(t["amount"] for t in x[1]),
            reverse=True,
        ):
            group_total = sum(t["amount"] for t in group_txns)
            visible = group_txns[:_MAX_DETAIL_ROWS]
            hidden = len(group_txns) - len(visible)
            amt_w = max(len(f"{t['amount']:,.0f}") for t in visible)
            table_lines = [
                f"{t['description']}  {t['amount']:>{amt_w},.0f} ₴  "
                f"{date.fromisoformat(t['date']).strftime('%-d %b')}"
                for t in visible
            ]
            if hidden:
                table_lines.append(f"+ {hidden} more…")
            header = f"{bold(group_label)}  {group_total:,.0f} ₴"
            parts.append(header + "\n" + pre("\n".join(table_lines)))
    else:
        # Flat table — no redundant label headers
        visible = txns[:_MAX_DETAIL_ROWS]
        hidden = len(txns) - len(visible)
        desc_w = max(len(t["description"]) for t in visible) if visible else 0
        amt_w = max(len(f"{t['amount']:,.0f}") for t in visible) if visible else 0
        table_lines = [
            f"{t['description']:<{desc_w}}  {t['amount']:>{amt_w},.0f} "
            f"{_sym(t.get('currency', 'UAH'))}  "
            f"{date.fromisoformat(t['date']).strftime('%-d %b')}"
            for t in visible
        ]
        if hidden:
            table_lines.append(f"+ {hidden} more…")
        parts.append(pre("\n".join(table_lines)))

    start = date.fromisoformat(data["period_start"])
    period_label = start.strftime("%b %-d")
    cat_header = f"{category}  {cat_row['amount']:,.0f} ₴  ({pct}%)"
    title = f"{em} {bold(cat_header)}"
    subtitle = italic(f"since {period_label}")
    return f"{title}\n{subtitle}\n\n" + "\n\n".join(parts)


def format_subscriptions(data: dict[str, Any]) -> str:
    """Format subscription breakdown: monthly, yearly, unknown frequency."""
    monthly = data.get("monthly", [])
    yearly = data.get("yearly", [])
    unknown = data.get("one_time", data.get("unknown", []))

    if not monthly and not yearly and not unknown:
        return "No subscriptions found in last 90 days."

    parts: list[str] = []

    def _table(items: list[dict[str, Any]], show_proj: bool) -> str:
        name_w = max(len(s["name"]) for s in items)
        amt_w = max(len(f"{s['amount']:,}") for s in items)
        lines = []
        for s in items:
            proj = (
                f"  → {s.get('yearly_equiv', s.get('yearly', 0)):,}/yr"
                if show_proj
                else f"  → {s.get('monthly_equiv', 0):,}/mo"
            )
            lines.append(f"{s['name']:<{name_w}}  {s['amount']:>{amt_w},} ₴{proj}")
        return "\n".join(lines)

    if monthly:
        total_yr = data["monthly_total"] * 12
        lines = _table(monthly, show_proj=True)
        div = "─" * max(len(row) for row in lines.splitlines())
        name_w = max(len(s["name"]) for s in monthly)
        mo_total = data["monthly_total"]
        total_line = f"{'Total':<{name_w}}  {mo_total:,} ₴  → {total_yr:,}/yr"
        parts.append(f"{bold('Monthly')}\n" + pre(lines + f"\n{div}\n{total_line}"))

    if yearly:
        lines = _table(yearly, show_proj=False)
        parts.append(f"{bold('Yearly')}\n" + pre(lines))

    if unknown:
        lines = "\n".join(f"  {s['name']}  {s['amount']:,} ₴" for s in unknown)
        parts.append(f"{italic('One-time or too new to classify')}\n{lines}")

    total_mo = data.get("total_per_month", 0)
    total_yr = data.get("total_per_year", 0)
    footer = bold(f"Total  {total_mo:,} ₴/mo  →  {total_yr:,} ₴/yr")
    return f"📱 {bold('Subscriptions')}\n\n" + "\n\n".join(parts) + f"\n\n{footer}"


def format_stats(spending: dict[str, float], period: str = "this_month") -> str:
    """Format spending breakdown as HTML."""
    if not spending:
        return f"No spending data for {_PERIOD_LABEL.get(period, period)}."
    total = sum(spending.values())
    label = _PERIOD_LABEL.get(period, period)
    lines = [bold(f"📊 Spending — {label}"), ""]
    for category_name, amount in sorted(
        spending.items(), key=lambda x: x[1], reverse=True
    ):
        pct = round(amount / total * 100) if total else 0
        em = _emoji(category_name)
        lines.append(
            f"{em} {bold(category_name)}  {amount:,.0f} ₴  {italic(f'{pct}%')}"
        )
    lines += ["", bold(f"Total: {total:,.0f} ₴")]
    return "\n".join(lines)


def format_budget(budgets: list[dict[str, Any]]) -> str:
    """Format budget limits vs spending as HTML."""
    label = date.today().strftime("%B %Y")
    if not budgets:
        return (
            f"{bold(f'📉 Budget — {label}')}\n\n"
            "No limits set yet.\n"
            f"Use {code('/budget set <category> <amount>')} to add one."
        )
    lines = [bold(f"📉 Budget — {label}"), ""]
    for b in budgets:
        em = _emoji(b["category"])
        spent = b["spent"]
        limit = b["monthly_limit"]
        sym = _sym(b["currency"])
        if b["exceeded"]:
            over = spent - limit
            lines.append(
                f"{em} {bold(b['category'])}  {spent:,.0f} / {limit:,.0f} {sym}  "
                f"⚠️ {italic(f'over by {over:,.0f}')}"
            )
        else:
            left = b["remaining"]
            lines.append(
                f"{em} {bold(b['category'])}  {spent:,.0f} / {limit:,.0f} {sym}  "
                f"✅ {italic(f'{left:,.0f} left')}"
            )
    return "\n".join(lines)


def format_sync_status(status: dict[str, Any]) -> str:
    """Format sync status as HTML."""
    s = status.get("status", "unknown")
    if s == "never_synced":
        return "🔄 Sync started. No previous run on record."
    if s == "running":
        started = status.get("started_at", "—")
        return f"🔄 Sync in progress…\nStarted: {started}"
    imported = status.get("tx_imported", 0)
    completed = status.get("completed_at", "—")
    error = status.get("error")
    if s == "error":
        return f"❌ Last sync failed.\nError: {error}\nCompleted: {completed}"
    return (
        f"✅ Sync complete.\n{imported} transactions imported\nCompleted: {completed}"
    )
