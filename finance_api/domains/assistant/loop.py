"""Conversational agent for free-form money questions.

Scoped to read-only Finance API queries and OpenRouter's OpenAI-compatible
chat-completions API.
"""

import asyncio
import json
from datetime import date
from uuid import UUID

import httpx
import structlog

from finance_api.core.config import settings
from finance_api.core.product import APP_NAME, OPENROUTER_CHAT_COMPLETIONS_URL
from finance_api.domains.bot.language import get_language
from finance_api.domains.budgets.queries import list_budgets_vs_spending
from finance_api.domains.insights.queries import (
    get_account_balances,
    get_income_summary,
    get_monthly_trend,
    get_recent_transactions,
    get_spending_by_category,
    get_subscriptions,
    get_sync_health,
)
from finance_api.domains.transactions.labeling import (
    edit_latest_transaction,
    label_latest_uncategorized,
    label_transaction_by_id,
    relabel_latest_transaction,
)
from finance_api.domains.transactions.manual import record_manual_income

log = structlog.get_logger(__name__)

_OPENROUTER_URL = OPENROUTER_CHAT_COMPLETIONS_URL
_MAX_TOOL_TURNS = 8  # safety cap on tool-calling round-trips per message
_MAX_HISTORY = 20  # trimmed message count kept per chat

_sessions: dict[int, list[dict]] = {}

_TOOL_DEFS: list[dict] = [
    {
        "name": "get_balances",
        "description": "Current balances for all visible accounts.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_spending",
        "description": "Spending grouped by category for a period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": (
                        "this_month, last_month, last_7d, last_30d, or last_90d"
                    ),
                },
            },
        },
    },
    {
        "name": "get_monthly_trend",
        "description": "Month-by-month income vs. expenses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "months": {"type": "integer", "description": "Defaults to 3."},
            },
        },
    },
    {
        "name": "get_recent_transactions",
        "description": "Most recent transactions, optionally filtered by period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Defaults to 20."},
                "period": {
                    "type": "string",
                    "description": "this_month, last_month, last_7d, etc.",
                },
            },
        },
    },
    {
        "name": "get_budgets",
        "description": "Budget limits vs. actual spending this month.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_subscriptions",
        "description": "Detected recurring subscriptions.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_income_summary",
        "description": "Income summary for the current period.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_sync_status",
        "description": "When the bank data was last synced, and its outcome.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "record_income",
        "description": (
            "Record income that did not arrive through Monobank, for example cash, "
            "Wise, PayPal, or another bank. Use only when the user explicitly asks "
            "to record/add income."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "currency": {"type": "string", "description": "UAH, USD, EUR, etc."},
                "description": {"type": "string"},
                "date": {
                    "type": "string",
                    "description": "ISO date YYYY-MM-DD. Omit for today.",
                },
                "notes": {"type": "string"},
            },
            "required": ["amount", "currency", "description"],
        },
    },
    {
        "name": "label_uncategorized",
        "description": (
            "Set a category for the newest uncategorized transaction matching "
            "a description fragment. Use when the user answers what an unknown "
            "transaction was."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "category": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["description", "category"],
        },
    },
    {
        "name": "label_transaction",
        "description": (
            "Set a category for a specific transaction id selected by the "
            "uncategorized review flow. Also save any user-provided free-text "
            "description/tags as notes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string"},
                "category": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["transaction_id", "category"],
        },
    },
    {
        "name": "relabel_transaction",
        "description": (
            "Change category for an existing already-labeled transaction. Use when "
            "the user says a transaction should be another category, including batch "
            "relabel requests. Match by description fragment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "category": {"type": "string"},
            },
            "required": ["description", "category"],
        },
    },
    {
        "name": "edit_transaction",
        "description": (
            "Apply a small correction to the newest transaction matching a description "
            "fragment: amount, description, date, notes, category, or mode. Use only "
            "when the user clearly asks to change stored data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "match": {"type": "string"},
                "amount": {"type": "number"},
                "description": {"type": "string"},
                "date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "notes": {"type": "string"},
                "category": {"type": "string"},
                "mode": {"type": "string", "description": "solo, couple, or null"},
            },
            "required": ["match"],
        },
    },
]

_OPENAI_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }
    for tool in _TOOL_DEFS
]

_SYSTEM = (
    f"You are the user's personal finance assistant, built into {APP_NAME}. "
    "Answer conversational questions about Monobank accounts, spending, "
    "budgets, income, and subscriptions using the tools provided — never guess "
    "at numbers.\n\n"
    "Rules:\n"
    "- Always call get_balances first before answering any money question, so "
    "you have current context. Exception: for transaction labeling prompts, do "
    "not call get_balances; label the transaction directly. If accounts come "
    "back empty, ask the user to tap the 🔄 Sync button.\n"
    "- Keep answers short and conversational — a sentence or two, not a report.\n"
    "- Use these category emojis when listing spending: 🛒 Groceries, "
    "🍔 Restaurants, 🚇 Transport, 🏠 Housing, 💊 Health, 👗 Clothes, "
    "🛍️ Shopping, 🎮 Entertainment, ✈️ Travel, 💳 Financial, 💸 Transfers, "
    "💰 Income, 📦 Other.\n"
    "- Mind currencies — never sum or compare amounts across different currencies.\n"
    "- If the user says to record/add cash or non-bank income, call record_income, "
    "then confirm the amount, currency, and description.\n"
    "- If the user answers what an uncategorized transaction is, call "
    "label_uncategorized with the transaction description fragment and one "
    "canonical category name. If the user gave extra descriptive tags/notes, "
    "pass them as notes.\n"
    "- If the prompt includes a selected transaction id from the uncategorized "
    "review flow, interpret the user's free text, choose the closest canonical "
    "category, and call label_transaction with that id. If it includes a "
    "selected transaction description instead, call label_uncategorized with "
    "that description. If the user gave extra descriptive tags/notes, pass "
    "them as notes.\n"
    "- If the user wants to change a category on an already-labeled transaction, "
    "call relabel_transaction. For several changes, call it once per item.\n"
    "- If the user wants to slightly correct stored transaction data, call "
    "edit_transaction. Do not change data unless the request is clear.\n"
    "- This is a Telegram chat: reply in valid Telegram HTML. Use only simple "
    "tags like <b>, <i>, and <code>; no Markdown.\n"
    "- Message format: start with a short bold result line, then 1-3 compact "
    "lines only if useful. Put amounts, dates, and transaction fragments in "
    "<code>. Avoid tables. End with one clear next step only when the user needs "
    "to do something."
)


async def _dispatch_tool(
    name: str, tool_input: dict, user_id: UUID | None = None
) -> str:
    """Run the named read-only query and return a JSON string result."""
    try:
        if user_id is not None and name not in {
            "get_balances",
            "get_spending",
            "label_uncategorized",
            "label_transaction",
        }:
            return "Error: this tool is not user-scoped yet"
        if name == "get_balances":
            result = await asyncio.to_thread(get_account_balances, 0, user_id)
        elif name == "get_spending":
            result = await asyncio.to_thread(
                get_spending_by_category,
                period=tool_input.get("period", "this_month"),
                user_id=user_id,
            )
        elif name == "get_monthly_trend":
            result = await asyncio.to_thread(
                get_monthly_trend, months=tool_input.get("months", 3)
            )
        elif name == "get_recent_transactions":
            result = await asyncio.to_thread(
                get_recent_transactions,
                limit=tool_input.get("limit", 20),
                period=tool_input.get("period"),
            )
        elif name == "get_budgets":
            items = await asyncio.to_thread(list_budgets_vs_spending)
            result = [item.model_dump() for item in items]
        elif name == "get_subscriptions":
            result = await asyncio.to_thread(get_subscriptions)
        elif name == "get_income_summary":
            result = await asyncio.to_thread(get_income_summary)
        elif name == "get_sync_status":
            result = await asyncio.to_thread(get_sync_health)
        elif name == "record_income":
            received_on = None
            if tool_input.get("date"):
                received_on = date.fromisoformat(str(tool_input["date"]))
            result = await asyncio.to_thread(
                record_manual_income,
                amount=float(tool_input["amount"]),
                currency=str(tool_input["currency"]),
                description=str(tool_input["description"]),
                received_on=received_on,
                notes=tool_input.get("notes"),
            )
        elif name == "label_uncategorized":
            result = await asyncio.to_thread(
                label_latest_uncategorized,
                description=str(tool_input["description"]),
                category=str(tool_input["category"]),
                notes=tool_input.get("notes"),
            )
        elif name == "label_transaction":
            result = await asyncio.to_thread(
                label_transaction_by_id,
                str(tool_input["transaction_id"]),
                str(tool_input["category"]),
                notes=tool_input.get("notes"),
            )
        elif name == "relabel_transaction":
            result = await asyncio.to_thread(
                relabel_latest_transaction,
                description=str(tool_input["description"]),
                category=str(tool_input["category"]),
            )
        elif name == "edit_transaction":
            kwargs = {
                key: value
                for key, value in tool_input.items()
                if key in {"amount", "description", "date", "notes", "category", "mode"}
            }
            result = await asyncio.to_thread(
                edit_latest_transaction,
                str(tool_input["match"]),
                **kwargs,
            )
        else:
            return f"Unknown tool: {name}"
    except Exception as exc:
        log.warning("assistant_tool_error", tool=name, error=str(exc))
        return f"Error: {exc}"
    return json.dumps(result, default=str)


def _system_prompt() -> str:
    language = get_language()
    if language == "uk":
        return _SYSTEM + "\n- Reply in Ukrainian."
    return _SYSTEM + "\n- Reply in English."


async def _chat(messages: list[dict]) -> dict:
    """Call OpenRouter's OpenAI-compatible chat completions API."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            _OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.agent_model,
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    *messages,
                ],
                "tools": _OPENAI_TOOLS,
                "tool_choice": "auto",
                "max_tokens": 1024,
            },
        )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]


async def answer(chat_id: int, text: str, user_id: UUID | None = None) -> str:
    """Run one conversational turn for `chat_id` and return the reply text.

    Keeps a short rolling history per chat (in-memory; resets on redeploy) so
    follow-up questions retain context.
    """
    messages = _sessions.setdefault(chat_id, [])
    messages.append({"role": "user", "content": text})

    reply = "Sorry, I couldn't come up with an answer."
    for _ in range(_MAX_TOOL_TURNS):
        message = await _chat(messages)
        content = message.get("content") or ""
        if content:
            reply = content

        tool_calls = message.get("tool_calls") or []
        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
        })
        if not tool_calls:
            break

        for call in tool_calls:
            function = call.get("function") or {}
            name = function.get("name", "")
            try:
                tool_input = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                tool_input = {}
            result = await _dispatch_tool(name, tool_input, user_id=user_id)
            log.info("assistant_tool_called", tool=name)
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": result,
            })

    del messages[:-_MAX_HISTORY]
    return reply
