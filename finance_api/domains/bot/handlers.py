"""Telegram command handlers for the finance bot."""

import asyncio

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from finance_api.bot.telegram_fmt import PARSE_MODE, code
from finance_api.core.config import settings
from finance_api.core.product import APP_TITLE, BOT_OPEN_BUTTON_TEXT
from finance_api.domains.assistant.loop import answer as assistant_answer
from finance_api.domains.bot.formatter import (
    format_balance,
    format_month_report,
    format_spending_category,
    format_spending_summary,
    format_subscriptions,
    format_sync_status,
)
from finance_api.domains.insights.queries import (
    get_account_balances,
    get_hidden_account_balances,
    get_income_summary,
    get_month_cycle_summary,
    get_spending_summary,
    get_subscriptions,
    get_sync_health,
    get_visible_account_count,
)
from finance_api.domains.sync.monobank import run_sync

log = structlog.get_logger(__name__)

SYNC_CALLBACK = "sync"
INCOME_CALLBACK = "income"
SPENDING_CALLBACK = "spending"
MONTH_CALLBACK = "month"
SPENDING_CAT_PREFIX = "spd:"
SUBS_CALLBACK = "subs"
SKIPPED_CALLBACK = "skipped"
BALANCE_CALLBACK = "balance_cb"

_MSG_NOT_MODIFIED = "message is not modified"
_background_tasks: set[asyncio.Task] = set()


def _run_background(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def _balance_keyboard() -> InlineKeyboardMarkup:
    return _main_keyboard(0)


def _month_label(offset: int) -> str:
    from finance_api.domains.insights.queries import selected_month_label

    return selected_month_label(offset)


def _main_keyboard(offset: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💳 Balance", callback_data=f"{BALANCE_CALLBACK}:{offset}"
            ),
            InlineKeyboardButton(
                f"📅 {_month_label(offset)}", callback_data=f"{MONTH_CALLBACK}:{offset}"
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 Spending", callback_data=f"{SPENDING_CALLBACK}:{offset}"
            ),
            InlineKeyboardButton("🔄 Sync", callback_data=SYNC_CALLBACK),
        ],
    ])


def _month_keyboard(summary: dict) -> InlineKeyboardMarkup:
    offset = int(summary.get("offset", 0))
    row = [InlineKeyboardButton("← Prev", callback_data=f"month:{offset + 1}")]
    row.append(
        InlineKeyboardButton(
            f"📅 {_month_label(offset)}", callback_data=f"month:{offset}"
        )
    )
    if summary.get("has_next"):
        row.append(InlineKeyboardButton("Next →", callback_data=f"month:{offset - 1}"))
    return InlineKeyboardMarkup([
        row,
        [InlineKeyboardButton("← Back", callback_data=f"{BALANCE_CALLBACK}:{offset}")],
    ])


def _callback_offset(data: str | None, default: int = 0) -> int:
    raw = str(data or "")
    if ":" not in raw:
        return default
    try:
        return max(0, int(raw.split(":", 1)[1]))
    except ValueError:
        return default


def _thread_id(message) -> int | None:
    """Return the forum topic thread ID for a message, or None outside topics."""
    return getattr(message, "message_thread_id", None)


def _is_group_chat(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type != "private")


def _is_reply_to_bot(message: Message, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    reply = getattr(message, "reply_to_message", None)
    sender = getattr(reply, "from_user", None) if reply else None
    bot_id = getattr(ctx.bot, "id", None)
    return bool(sender and bot_id and sender.id == bot_id)


def _strip_bot_mention(text: str, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    username = getattr(ctx.bot, "username", None)
    if not username:
        return text.strip()
    return text.replace(f"@{username}", "").strip()


def _should_answer_group_text(message: Message, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    username = getattr(ctx.bot, "username", None)
    mentioned = bool(username and f"@{username}" in (message.text or ""))
    return mentioned or _is_reply_to_bot(message, ctx)


async def _edit(query, text: str, **kwargs) -> None:
    """Edit the message in place; silently ignore if content is unchanged."""
    try:
        await query.edit_message_text(text, **kwargs)
    except BadRequest as e:
        if _MSG_NOT_MODIFIED not in str(e).lower():
            raise


_MONO_RATE_LIMIT_S = 62  # Monobank allows one request per 62 s per token
_sync_running = False


async def _sync_then_edit(message: Message) -> None:
    """Background task: run sync and edit message with the final status."""
    global _sync_running
    try:
        await asyncio.to_thread(run_sync)
        status = await asyncio.to_thread(get_sync_health)
        try:
            await message.edit_text(
                format_sync_status(status),
                parse_mode=PARSE_MODE,
                reply_markup=_balance_keyboard(),
            )
        except BadRequest as e:
            if _MSG_NOT_MODIFIED not in str(e).lower():
                raise
    finally:
        _sync_running = False


async def _do_sync(message: Message) -> None:
    """For /sync command — reply with status message, edit it when done."""
    n = await asyncio.to_thread(get_visible_account_count)
    est_min = max(1, round(n * _MONO_RATE_LIMIT_S / 60))
    sent = await message.reply_text(
        f"🔄 Syncing…  ~{est_min} min", parse_mode=PARSE_MODE
    )
    _run_background(_sync_then_edit(sent))


async def cmd_finance_app(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /finance_app command — open the Mini App."""
    url = settings.mini_app_url
    # Use a plain URL button everywhere — InlineKeyboardButton.web_app requires
    # the domain to be approved in BotFather, which fails with Button_type_invalid
    # until that is configured.
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(BOT_OPEN_BUTTON_TEXT, url=url)]
    ])
    text = APP_TITLE
    in_finance_topic = (
        settings.telegram_chat_id is not None
        and update.effective_chat.id == settings.telegram_chat_id
        and _thread_id(update.message) == settings.telegram_finance_topic_id
    )
    if (
        in_finance_topic
        or update.effective_chat.type == "private"
        or settings.telegram_chat_id is None
    ):
        await update.message.reply_text(text, reply_markup=keyboard)
    else:
        await ctx.bot.send_message(
            chat_id=settings.telegram_chat_id,
            message_thread_id=settings.telegram_finance_topic_id,
            text=text,
            reply_markup=keyboard,
        )


async def balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /balance command."""
    try:
        accounts = await asyncio.to_thread(get_account_balances, 0)
        month = await asyncio.to_thread(get_month_cycle_summary, 0)
        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=_thread_id(update.message),
            text=format_balance(accounts, month),
            parse_mode=PARSE_MODE,
            reply_markup=_main_keyboard(0),
        )
    except Exception as e:
        log.error("balance_failed", error=str(e))
        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=_thread_id(update.message),
            text=f"❌ Error: {code(e)}",
            parse_mode=PARSE_MODE,
        )


async def callback_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 💳 Balance button — edit message with fresh balance."""
    query = update.callback_query
    await query.answer()
    try:
        offset = _callback_offset(query.data)
        accounts = await asyncio.to_thread(get_account_balances, offset)
        month = await asyncio.to_thread(get_month_cycle_summary, offset)
        await _edit(
            query,
            format_balance(accounts, month),
            parse_mode=PARSE_MODE,
            reply_markup=_main_keyboard(offset),
        )
    except Exception as e:
        log.error("balance_callback_failed", error=str(e))
        await _edit(query, f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


async def callback_income(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 💰 Income button — edit message with income/spending summary."""
    query = update.callback_query
    await query.answer()
    try:
        income = await asyncio.to_thread(get_income_summary, 0)
        text = format_month_report(income, {})
        await _edit(query, text, parse_mode=PARSE_MODE, reply_markup=_main_keyboard(0))
    except Exception as e:
        log.error("income_callback_failed", error=str(e))
        await _edit(query, f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


async def callback_skipped(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 👁 Skipped button — edit message with hidden accounts."""
    query = update.callback_query
    await query.answer()
    try:
        accounts = await asyncio.to_thread(get_hidden_account_balances)
        text = format_balance(accounts) if accounts else "No skipped accounts."
        await _edit(
            query, text, parse_mode=PARSE_MODE, reply_markup=_balance_keyboard()
        )
    except Exception as e:
        log.error("skipped_callback_failed", error=str(e))
        await _edit(query, f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


_CAT_SHORT: dict[str, str] = {
    "Food & Drink": "Food",
    "Groceries": "Groceries",
    "Transportation": "Transport",
    "Healthcare": "Health",
    "Shopping": "Shopping",
    "Entertainment": "Fun",
    "Travel": "Travel",
    "Subscriptions": "Subs",
    "Utilities": "Utils",
    "ATM & Cash": "Cash",
    "Finance": "Finance",
    "Education": "Education",
    "Pets": "Pets",
    "Partner": "Partner",
}


def _spending_keyboard(data: dict) -> InlineKeyboardMarkup:
    """Category buttons (emoji + short name) + back-to-balance row."""
    from finance_api.domains.bot.formatter import CATEGORY_EMOJI
    from finance_api.domains.transactions.categories import CASHBACK, COUPLE_TRANSFER

    rows_data = [
        r
        for r in data.get("rows", [])
        if r["currency"] == "UAH" and r["category"] not in {COUPLE_TRANSFER, CASHBACK}
    ]
    rows_data.sort(key=lambda r: r["amount"], reverse=True)
    offset = int(data.get("offset", 0))
    cat_buttons = [
        InlineKeyboardButton(
            f"{CATEGORY_EMOJI.get(r['category'], '📦')} "
            f"{_CAT_SHORT.get(r['category'], r['category'])}",
            callback_data=f"{SPENDING_CAT_PREFIX}{offset}:{r['category']}",
        )
        for r in rows_data
    ]
    # Split into rows of 3
    keyboard = [cat_buttons[i : i + 3] for i in range(0, len(cat_buttons), 3)]
    offset = int(data.get("offset", 0))
    keyboard.append([
        InlineKeyboardButton("🔁 Subs", callback_data=f"{SUBS_CALLBACK}:{offset}"),
        InlineKeyboardButton("← Back", callback_data=f"{BALANCE_CALLBACK}:{offset}"),
    ])
    return InlineKeyboardMarkup(keyboard)


async def callback_spending(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 📊 Spending button — edit message with salary-cycle spending breakdown."""
    query = update.callback_query
    await query.answer()
    try:
        offset = _callback_offset(query.data)
        data = await asyncio.to_thread(get_spending_summary, offset)
        ctx.user_data["spending_data"] = data
        text = format_spending_summary(data) or "No spending recorded yet this month."
        await _edit(
            query, text, parse_mode=PARSE_MODE, reply_markup=_spending_keyboard(data)
        )
    except Exception as e:
        log.error("spending_callback_failed", error=str(e))
        await _edit(query, f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


async def callback_month(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 📅 Month button — show salary-cycle month management summary."""
    query = update.callback_query
    await query.answer()
    try:
        offset = _callback_offset(query.data)
        summary = await asyncio.to_thread(get_month_cycle_summary, offset)
        await _edit(
            query,
            f"📅 <b>Month</b>\n{_month_label(offset)}",
            parse_mode=PARSE_MODE,
            reply_markup=_month_keyboard(summary),
        )
    except Exception as e:
        log.error("month_callback_failed", error=str(e))
        await _edit(query, f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


async def callback_spending_category(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle category drill-down button — show detail for selected category."""
    query = update.callback_query
    await query.answer()
    category_data = query.data[len(SPENDING_CAT_PREFIX) :]
    offset = 0
    if ":" in category_data:
        maybe_offset, category_data = category_data.split(":", 1)
        if maybe_offset.isdigit():
            offset = int(maybe_offset)
    category = category_data
    try:
        data = ctx.user_data.get("spending_data") or await asyncio.to_thread(
            get_spending_summary, offset
        )
        ctx.user_data["spending_data"] = data
        text = format_spending_category(data, category)
        offset = int(data.get("offset", 0))
        back_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "← Spending", callback_data=f"{SPENDING_CALLBACK}:{offset}"
                )
            ]
        ])
        await _edit(query, text, parse_mode=PARSE_MODE, reply_markup=back_kb)
    except Exception as e:
        log.error("spending_cat_failed", error=str(e))
        await _edit(query, f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


async def callback_subs(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 📱 Subs button — edit message with subscription breakdown."""
    query = update.callback_query
    await query.answer()
    try:
        offset = _callback_offset(query.data)
        data = await asyncio.to_thread(get_subscriptions, offset)
        text = format_subscriptions(data)
        await _edit(
            query,
            text,
            parse_mode=PARSE_MODE,
            reply_markup=_spending_keyboard({"rows": [], "offset": offset}),
        )
    except Exception as e:
        log.error("subs_callback_failed", error=str(e))
        await _edit(query, f"❌ Error: {code(e)}", parse_mode=PARSE_MODE)


async def sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sync command."""
    try:
        await _do_sync(update.message)
    except Exception as e:
        log.error("sync_failed", error=str(e))
        await update.message.reply_text(
            f"❌ Sync failed: {code(e)}", parse_mode=PARSE_MODE
        )


async def callback_sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 🔄 Sync button — edit message to syncing state, update when done."""
    global _sync_running
    query = update.callback_query
    await query.answer()
    n = await asyncio.to_thread(get_visible_account_count)
    est_min = max(1, round(n * _MONO_RATE_LIMIT_S / 60))
    if _sync_running:
        # Sync already running — just show progress, don't start a second one
        await _edit(
            query,
            f"🔄 Syncing…  ~{est_min} min",
            parse_mode=PARSE_MODE,
            reply_markup=_main_keyboard(0),
        )
        return
    _sync_running = True
    try:
        await _edit(
            query,
            f"🔄 Syncing…  ~{est_min} min",
            parse_mode=PARSE_MODE,
            reply_markup=_main_keyboard(0),
        )
        _run_background(_sync_then_edit(query.message))
    except Exception as e:
        _sync_running = False
        log.error("sync_callback_failed", error=str(e))
        await _edit(query, f"❌ Sync failed: {code(e)}", parse_mode=PARSE_MODE)


async def chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-form text — conversational money Q&A via the assistant.

    Registered last so it only fires when no command/callback matched, leaving
    the existing button-driven flows untouched.
    """
    user = update.effective_user
    message = update.message
    if user is None or message is None or not message.text:
        return
    if user.id != settings.telegram_owner_id:
        return
    if _is_group_chat(update) and not _should_answer_group_text(message, ctx):
        return
    prompt = _strip_bot_mention(message.text, ctx)
    if not prompt:
        return
    await ctx.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    placeholder = await ctx.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=_thread_id(message),
        text="⏳ Thinking…",
        parse_mode=PARSE_MODE,
    )
    try:
        reply = await assistant_answer(update.effective_chat.id, prompt)
    except Exception as e:
        log.error("assistant_failed", error=str(e))
        reply = f"❌ Error: {code(e)}"
    await placeholder.edit_text(reply, parse_mode=PARSE_MODE)
