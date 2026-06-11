"""Assistant tool wiring tests."""

import json
from datetime import date

import pytest

from finance_api.domains.assistant import loop


@pytest.mark.asyncio
async def test_record_income_tool_calls_manual_recorder(monkeypatch):
    calls = []

    def fake_record_manual_income(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "amount": kwargs["amount"]}

    monkeypatch.setattr(loop, "record_manual_income", fake_record_manual_income)

    result = await loop._dispatch_tool(
        "record_income",
        {
            "amount": 2500,
            "currency": "usd",
            "description": "Cash consulting",
            "date": "2026-06-10",
            "notes": "from chat",
        },
    )

    assert json.loads(result) == {"ok": True, "amount": 2500}
    assert calls == [
        {
            "amount": 2500,
            "currency": "usd",
            "description": "Cash consulting",
            "received_on": date(2026, 6, 10),
            "notes": "from chat",
        }
    ]


@pytest.mark.asyncio
async def test_relabel_transaction_tool_calls_relabeler(monkeypatch):
    calls = []

    def fake_relabel_latest_transaction(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "category": kwargs["category"]}

    monkeypatch.setattr(
        loop, "relabel_latest_transaction", fake_relabel_latest_transaction
    )

    result = await loop._dispatch_tool(
        "relabel_transaction",
        {"description": "нова", "category": "Couple Transfer"},
    )

    assert json.loads(result) == {"ok": True, "category": "Couple Transfer"}
    assert calls == [{"description": "нова", "category": "Couple Transfer"}]


@pytest.mark.asyncio
async def test_edit_transaction_tool_calls_editor(monkeypatch):
    calls = []

    def fake_edit_latest_transaction(description, **kwargs):
        calls.append({"description": description, **kwargs})
        return {"ok": True, "amount": kwargs["amount"]}

    monkeypatch.setattr(loop, "edit_latest_transaction", fake_edit_latest_transaction)

    result = await loop._dispatch_tool(
        "edit_transaction",
        {"match": "cash", "amount": 1200, "notes": "fixed"},
    )

    assert json.loads(result) == {"ok": True, "amount": 1200}
    assert calls == [{"description": "cash", "amount": 1200, "notes": "fixed"}]


def test_record_income_tool_is_exposed_to_openrouter():
    names = [tool["function"]["name"] for tool in loop._OPENAI_TOOLS]
    assert "record_income" in names
    assert "label_uncategorized" in names
    assert "relabel_transaction" in names
    assert "edit_transaction" in names


def test_system_prompt_requires_telegram_html(monkeypatch):
    monkeypatch.setattr(loop, "get_language", lambda: "en")

    prompt = loop._system_prompt()

    assert "Telegram HTML" in prompt
    assert "no Markdown" in prompt
