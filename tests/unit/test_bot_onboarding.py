"""Bot onboarding tests."""

from finance_api.domains.bot import formatter
from finance_api.domains.bot.handlers import is_allowed_user


def test_onboarding_message_has_monobank_token_link_and_ai_note():
    text = formatter.format_onboarding_message()

    assert "Monobank" in text
    assert "https://api.monobank.ua/" in text
    assert "AI" in text
    assert "/sync" in text


def test_allowed_user_accepts_owner_and_configured_extra_ids(monkeypatch):
    monkeypatch.setattr(
        "finance_api.domains.bot.handlers.settings.telegram_owner_id", 10
    )
    monkeypatch.setattr(
        "finance_api.domains.bot.handlers.settings.telegram_allowed_user_ids",
        "20, 30",
        raising=False,
    )

    assert is_allowed_user(10)
    assert is_allowed_user(20)
    assert is_allowed_user(30)
    assert not is_allowed_user(40)
