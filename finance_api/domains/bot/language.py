"""Persistent bot language preference."""

from sqlmodel import Session, select

from finance_api.core.db.engine import engine
from finance_api.domains.rules.models import TransactionRule

DEFAULT_LANGUAGE = "en"
LANGUAGES = {
    "en": "English",
    "uk": "Українська",
}
_RULE_TYPE = "bot_language"
_PATTERN = "default"


def get_language() -> str:
    """Return current bot language code."""
    with Session(engine) as session:
        rule = session.exec(
            select(TransactionRule).where(
                TransactionRule.rule_type == _RULE_TYPE,
                TransactionRule.pattern == _PATTERN,
            )
        ).first()
        if rule and rule.label in LANGUAGES:
            return rule.label
    return DEFAULT_LANGUAGE


def set_language(language: str) -> str:
    """Persist bot language code."""
    if language not in LANGUAGES:
        raise ValueError(f"Unknown language '{language}'")

    with Session(engine) as session:
        rule = session.exec(
            select(TransactionRule).where(
                TransactionRule.rule_type == _RULE_TYPE,
                TransactionRule.pattern == _PATTERN,
            )
        ).first()
        if rule is None:
            rule = TransactionRule(
                rule_type=_RULE_TYPE,
                pattern=_PATTERN,
                label=language,
            )
        else:
            rule.label = language
        session.add(rule)
        session.commit()
    return language


def language_name(language: str) -> str:
    """Display name for a language code."""
    return LANGUAGES.get(language, LANGUAGES[DEFAULT_LANGUAGE])
