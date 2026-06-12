"""Assistant behavior in Telegram groups."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from finance_api.domains.bot import handlers


@pytest.mark.asyncio
async def test_group_chat_ignores_plain_text(monkeypatch):
    monkeypatch.setattr(handlers.settings, "telegram_owner_id", 123)
    assistant = AsyncMock(return_value="<b>Done</b>")
    monkeypatch.setattr(handlers, "assistant_answer", assistant)

    ctx = MagicMock()
    ctx.bot.id = 999
    ctx.bot.username = "sova_finance_bot"
    ctx.bot.send_chat_action = AsyncMock()
    ctx.bot.send_message = AsyncMock()

    update = MagicMock()
    update.effective_user.id = 123
    update.effective_chat.id = -1001
    update.effective_chat.type = "supergroup"
    update.message.text = "what is my balance?"
    update.message.reply_to_message = None

    await handlers.chat(update, ctx)

    assistant.assert_not_awaited()
    ctx.bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_group_chat_answers_mentions_without_mention_in_prompt(monkeypatch):
    monkeypatch.setattr(handlers.settings, "telegram_owner_id", 123)
    assistant = AsyncMock(return_value="<b>Done</b>")
    monkeypatch.setattr(handlers, "assistant_answer", assistant)

    placeholder = AsyncMock()
    placeholder.edit_text = AsyncMock()

    ctx = MagicMock()
    ctx.bot.id = 999
    ctx.bot.username = "sova_finance_bot"
    ctx.bot.send_chat_action = AsyncMock()
    ctx.bot.send_message = AsyncMock(return_value=placeholder)

    update = MagicMock()
    update.effective_user.id = 123
    update.effective_chat.id = -1001
    update.effective_chat.type = "supergroup"
    update.message.text = "@sova_finance_bot what is my balance?"
    update.message.message_thread_id = 321
    update.message.reply_to_message = None

    await handlers.chat(update, ctx)

    assistant.assert_awaited_once_with(-1001, "what is my balance?")
    ctx.bot.send_message.assert_awaited_once()
    placeholder.edit_text.assert_awaited_once()
