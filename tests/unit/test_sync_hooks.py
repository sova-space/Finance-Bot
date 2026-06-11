"""New transaction notification tests."""

from finance_api.domains.transactions import categories as cat


def test_format_new_transaction_message_for_known_food_is_short_and_playful(
    monkeypatch,
):
    from finance_api.domains.sync import hooks

    monkeypatch.setattr(hooks, "get_language", lambda: "en")

    text = hooks.format_new_transaction_message({
        "description": "SHOCKO CAFE",
        "amount": -420,
        "currency": "UAH",
        "category": cat.FOOD_AND_DRINK,
    })

    assert "SHOCKO CAFE" in text
    assert "420" in text
    assert "ate well" in text
    assert "What category" not in text


def test_format_new_transaction_message_for_uncategorized_asks_question(monkeypatch):
    from finance_api.domains.sync import hooks

    monkeypatch.setattr(hooks, "get_language", lambda: "en")

    text = hooks.format_new_transaction_message({
        "description": "UNKNOWN SHOP",
        "amount": -100,
        "currency": "UAH",
        "category": None,
    })

    assert "UNKNOWN SHOP" in text
    assert "What category is this" in text
    assert "Food & Drink" in text


def test_format_new_transaction_message_for_big_income_celebrates_salary(monkeypatch):
    from finance_api.domains.sync import hooks

    monkeypatch.setattr(hooks, "get_language", lambda: "en")

    text = hooks.format_new_transaction_message({
        "description": "Salary",
        "amount": 40000,
        "currency": "UAH",
        "category": cat.INCOME,
    })

    assert "Salary" in text
    assert "wow" in text.lower()
    assert "cool" in text.lower()
