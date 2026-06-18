"""Deterministic transaction autolabeling from comments and learned rules."""

from sqlmodel import Session, select

from finance_api.domains.rules.models import TransactionRule
from finance_api.domains.transactions import categories as cat
from finance_api.domains.transactions import modes
from finance_api.domains.transactions.models import Transaction
from finance_api.domains.trips.models import Trip

AUTO_CATEGORY_RULE = "auto_category"

_CATEGORY_ALIASES: dict[str, str] = {
    "food": cat.FOOD_AND_DRINK,
    "restaurant": cat.FOOD_AND_DRINK,
    "restaurants": cat.FOOD_AND_DRINK,
    "bar": cat.FOOD_AND_DRINK,
    "beer": cat.FOOD_AND_DRINK,
    "wine": cat.FOOD_AND_DRINK,
    "alcohol": cat.FOOD_AND_DRINK,
    "alcool": cat.FOOD_AND_DRINK,
    "алко": cat.FOOD_AND_DRINK,
    "алкоголь": cat.FOOD_AND_DRINK,
    "groceries": cat.GROCERIES,
    "grocery": cat.GROCERIES,
    "продукти": cat.GROCERIES,
    "transport": cat.TRANSPORTATION,
    "taxi": cat.TRANSPORTATION,
    "uber": cat.TRANSPORTATION,
    "bolt": cat.TRANSPORTATION,
    "shopping": cat.SHOPPING,
    "subs": cat.SUBSCRIPTIONS,
    "subscription": cat.SUBSCRIPTIONS,
    "subscriptions": cat.SUBSCRIPTIONS,
    "utilities": cat.UTILITIES,
    "utility": cat.UTILITIES,
    "travel": cat.TRAVEL,
    "trip": cat.TRAVEL,
    "finance": cat.FINANCE,
    "education": cat.EDUCATION,
    "pets": cat.PETS,
    "health": cat.HEALTHCARE,
    "sport": cat.HEALTHCARE,
}


def category_from_text(text: str | None) -> str | None:
    """Return a category found in free text, if it is clear."""
    if not text:
        return None
    lower = text.strip().lower()
    if not lower:
        return None

    canonical_by_lower = {name.lower(): name for name in cat.ALL}
    for name_lower, name in canonical_by_lower.items():
        if name_lower in lower:
            return name

    for alias, category in _CATEGORY_ALIASES.items():
        if alias in lower:
            return category
    return None


def apply_learned_autolabel(session: Session, tx: Transaction) -> bool:
    """Apply a learned receiver/category rule to tx. Returns True if changed."""
    lower = tx.description.lower()
    rules = session.exec(
        select(TransactionRule).where(TransactionRule.rule_type == AUTO_CATEGORY_RULE)
    ).all()
    for rule in rules:
        if rule.pattern.lower() in lower and rule.label in cat.ALL:
            changed = tx.category != rule.label
            tx.category = rule.label
            if tx.amount < 0 and tx.mode is None:
                tx.mode = modes.SOLO
                changed = True
            return changed
    return False


def apply_comment_autolabel(session: Session, tx: Transaction) -> bool:
    """Use Monobank comment/notes to categorize and tag trips."""
    changed = False
    note = tx.notes or ""
    category = category_from_text(note)
    trip_name = _trip_name_from_comment(session, note)

    if trip_name:
        category = cat.TRAVEL
        extra = dict(tx.extra or {})
        if extra.get("trip") != trip_name:
            extra["trip"] = trip_name
            tx.extra = extra
            changed = True

    if category and tx.category != category:
        tx.category = category
        if tx.amount < 0 and tx.mode is None:
            tx.mode = modes.SOLO
        changed = True
        remember_receiver_category(session, tx.description, category)

    return changed


def autolabel_transaction(session: Session, tx: Transaction) -> bool:
    """Apply learned rules, then comment rules. Comment wins."""
    changed = apply_learned_autolabel(session, tx)
    if apply_comment_autolabel(session, tx):
        changed = True
    return changed


def _trip_name_from_comment(session: Session, comment: str) -> str | None:
    lower = comment.lower()
    if not lower:
        return None
    trips = session.exec(select(Trip)).all()
    for trip in trips:
        if trip.name.lower() in lower:
            return trip.name
    return None


def remember_receiver_category(
    session: Session,
    description: str,
    category: str,
) -> None:
    """Persist/update a receiver substring rule for future autolabeling."""
    pattern = description.strip()
    if not pattern or pattern.lower() == "monobank":
        return
    existing = session.exec(
        select(TransactionRule)
        .where(TransactionRule.rule_type == AUTO_CATEGORY_RULE)
        .where(TransactionRule.pattern == pattern)
    ).first()
    if existing:
        if existing.label != category:
            existing.label = category
            session.add(existing)
        return
    session.add(
        TransactionRule(
            rule_type=AUTO_CATEGORY_RULE,
            pattern=pattern,
            label=category,
        )
    )
