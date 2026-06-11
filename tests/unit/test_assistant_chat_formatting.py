"""Assistant chat Telegram formatting tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from finance_api.bot.telegram_fmt import PARSE_MODE
from finance_api.domains.assistant import loop
from finance_api.domains.bot import handlers


def test_system_prompt_teaches_concise_html_message_shapes(monkeypatch):
    monkeypatch.setattr(loop, "get_language", lambda: "en")

    prompt = loop._system_prompt()

    assert "Message format" in prompt
    assert "<b>" in prompt
    assert "<code>" in prompt
    assert "Avoid tables" in prompt
    assert "one clear next step" in prompt


@pytest.mark.asyncio
async def test_chat_edits_placeholder_message_with_html_reply(monkeypatch):
    monkeypatch.setattr(handlers.settings, "telegram_owner_id", 123)
    monkeypatch.setattr(
        handlers,
        "assistant_answer",
        AsyncMock(return_value="<b>Done</b>"),
    )

    placeholder = AsyncMock()
    placeholder.edit_text = AsyncMock()

    ctx = MagicMock()
    ctx.bot.send_chat_action = AsyncMock()
    ctx.bot.send_message = AsyncMock(return_value=placeholder)

    update = MagicMock()
    update.effective_user.id = 123
    update.effective_chat.id = 456
    update.message.text = "relabel nova as travel"
    update.message.message_thread_id = 789

    await handlers.chat(update, ctx)

    ctx.bot.send_message.assert_awaited_once_with(
        chat_id=456,
        message_thread_id=789,
        text="⏳ Thinking…",
        parse_mode=PARSE_MODE,
    )
    placeholder.edit_text.assert_awaited_once_with(
        "<b>Done</b>",
        parse_mode=PARSE_MODE,
    )
