"""Helpers for loading transaction classification rules from the database."""

from sqlmodel import Session, select

from finance_api.core.db.engine import engine
from finance_api.domains.rules.models import TransactionRule


def get_patterns(rule_type: str) -> list[str]:
    """Return all patterns for the given rule type."""
    with Session(engine) as session:
        rows = session.exec(
            select(TransactionRule.pattern).where(
                TransactionRule.rule_type == rule_type
            )
        ).all()
        return list(rows)


def get_rules(rule_type: str) -> list[tuple[str, str]]:
    """Return (pattern, label) pairs for the given rule type."""
    with Session(engine) as session:
        rows = session.exec(
            select(TransactionRule.pattern, TransactionRule.label).where(
                TransactionRule.rule_type == rule_type
            )
        ).all()
        return list(rows)


def matches_any(description: str, patterns: list[str]) -> bool:
    """Return True if description contains any pattern (case-insensitive)."""
    lower = description.lower()
    return any(p.lower() in lower for p in patterns)


def match_label(description: str, rules: list[tuple[str, str]]) -> str | None:
    """Return the label of the first matching rule, or None."""
    lower = description.lower()
    for pattern, label in rules:
        if pattern.lower() in lower:
            return label
    return None
