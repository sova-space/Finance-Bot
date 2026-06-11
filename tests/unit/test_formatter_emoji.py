"""Test that CATEGORY_EMOJI keys align with the canonical category list (Bug #4)."""

from finance_api.domains.bot.formatter import CATEGORY_EMOJI
from finance_api.domains.transactions import categories


def test_emoji_keys_are_subset_of_canonical_categories() -> None:
    """All keys in CATEGORY_EMOJI must exist in categories.ALL."""
    unknown = set(CATEGORY_EMOJI.keys()) - set(categories.ALL)
    assert not unknown, (
        f"CATEGORY_EMOJI contains non-canonical keys: {unknown}. "
        "Add them to categories.ALL or remove them from CATEGORY_EMOJI."
    )


def test_all_canonical_categories_have_emoji() -> None:
    """Every canonical category has an explicit emoji mapping."""
    missing = set(categories.ALL) - set(CATEGORY_EMOJI.keys())
    assert not missing, (
        f"Categories without emoji: {missing}. "
        "Add mappings to CATEGORY_EMOJI in formatter.py."
    )
