"""Async notification bridge for sync APScheduler threads.

APScheduler jobs run in background threads outside the asyncio event loop.
This module provides a thread-safe helper that posts messages to the Telegram
bot by scheduling a coroutine on the main event loop via
``asyncio.run_coroutine_threadsafe``.

Usage (from composition.py lifespan):

    from finance_api.domains.bot.notifications import set_notification_context
    set_notification_context(bot_app, asyncio.get_event_loop())

Usage (from any sync thread, e.g. a scheduler job):

    from finance_api.domains.bot.notifications import send_notification
    send_notification("Budget exceeded!", thread_id=topic_id)
"""

import asyncio
from typing import Any

import structlog

from finance_api.bot.telegram_fmt import PARSE_MODE
from finance_api.core.config import settings
from finance_api.core.product import APP_TITLE, BOT_OPEN_BUTTON_TEXT

log = structlog.get_logger(__name__)

_application: Any | None = None
_loop: asyncio.AbstractEventLoop | None = None


def set_notification_context(
    application: Any,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Store the running bot application and its event loop.

    Must be called once from the lifespan startup, after the bot is started.
    """
    global _application, _loop
    _application = application
    _loop = loop
    log.info("notification_context_set")


def send_finance_app_button() -> None:
    """Send the Mini App button to the #finance topic.

    Called via POST /bot/open when Hermes sees /finance_app.
    Uses a URL button because InlineKeyboardButton.web_app is private-chat only.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    if _application is None or _loop is None or settings.telegram_chat_id is None:
        log.warning("send_finance_app_button_skipped")
        return
    btn = InlineKeyboardButton(BOT_OPEN_BUTTON_TEXT, url=settings.mini_app_url)
    keyboard = InlineKeyboardMarkup([[btn]])
    asyncio.run_coroutine_threadsafe(
        _application.bot.send_message(
            chat_id=settings.telegram_chat_id,
            message_thread_id=settings.telegram_finance_topic_id,
            text=APP_TITLE,
            reply_markup=keyboard,
        ),
        _loop,
    )


def send_notification(text: str, thread_id: int | None = None) -> None:
    """Send a Telegram message from a sync APScheduler thread.

    Safe to call from any thread.  Does nothing if the notification context
    has not been set (e.g. during tests or when no bot token is configured).
    """
    if _application is None or _loop is None or settings.telegram_chat_id is None:
        log.warning("notification_context_not_set", text=text[:80])
        return
    asyncio.run_coroutine_threadsafe(
        _application.bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=text,
            message_thread_id=thread_id,
            parse_mode=PARSE_MODE,
        ),
        _loop,
    )
