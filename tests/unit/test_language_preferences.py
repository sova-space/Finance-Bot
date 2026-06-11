"""Language preference tests."""

from finance_api.domains.transactions import categories as cat


def test_language_defaults_to_english(session, monkeypatch):
    import finance_api.domains.bot.language as language

    monkeypatch.setattr(language, "engine", session.bind)

    assert language.get_language() == "en"


def test_set_language_persists_ukrainian(session, monkeypatch):
    import finance_api.domains.bot.language as language

    monkeypatch.setattr(language, "engine", session.bind)

    language.set_language("uk")

    assert language.get_language() == "uk"


def test_ukrainian_transaction_notification_uses_ukrainian_phrase(session, monkeypatch):
    import finance_api.domains.bot.language as language
    import finance_api.domains.sync.hooks as hooks

    monkeypatch.setattr(language, "engine", session.bind)
    language.set_language("uk")

    text = hooks.format_new_transaction_message({
        "description": "SHOCKO CAFE",
        "amount": -420,
        "currency": "UAH",
        "category": cat.FOOD_AND_DRINK,
    })

    assert "SHOCKO CAFE" in text
    assert "ото добре поїв" in text
