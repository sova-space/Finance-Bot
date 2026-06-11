"""Mini App HTML endpoint and bot trigger."""

import os
import threading

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

from finance_api.domains.assistant.loop import answer as assistant_answer
from finance_api.domains.bot.commands import BOT_COMMANDS
from finance_api.domains.bot.language import LANGUAGES, get_language, set_language
from finance_api.domains.bot.notifications import send_finance_app_button
from finance_api.domains.bot.ui import balance_keyboard, view_payload
from finance_api.domains.sync.monobank import run_sync

router = APIRouter()

_PROFILE = {
    "name": "finance",
    "description": "Money questions — balances, spending, budgets, transactions.",
    "dispatch_path": "/bot/assistant",
}


class AssistantRequest(BaseModel):
    """A domain question routed here from the profile router."""

    chat_id: int
    text: str


class AssistantResponse(BaseModel):
    """The assistant's answer, sent back to the router for delivery."""

    reply: str


class LanguageRequest(BaseModel):
    """Language selected by the general Hermes router."""

    language: str


_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@router.get("/miniapp", include_in_schema=False)
async def miniapp() -> FileResponse:
    """Serve the Telegram Mini App HTML shell."""
    path = os.path.join(_STATIC_DIR, "miniapp.html")
    return FileResponse(path, media_type="text/html")


@router.post("/bot/open", include_in_schema=False)
async def bot_open() -> dict:
    """Send the Mini App button to the #finance topic. Called by Hermes skill."""
    send_finance_app_button()
    return {"ok": True}


@router.get("/bot/commands", include_in_schema=False)
async def bot_commands() -> list[dict]:
    """Return registered bot commands. Hermes fetches this to stay in sync."""
    return [{"command": c.command, "description": c.description} for c in BOT_COMMANDS]


@router.get("/bot/language", include_in_schema=False)
async def bot_language() -> dict:
    """Return the service language synced from Hermes."""
    language = get_language()
    return {"language": language, "name": LANGUAGES[language]}


@router.put("/bot/language", include_in_schema=False)
async def bot_set_language(request: LanguageRequest) -> dict:
    """Persist the language selected in Hermes' general /language UI."""
    language = set_language(request.language)
    return {"language": language, "name": LANGUAGES[language]}


@router.get("/bot/profile", include_in_schema=False)
async def bot_profile() -> dict:
    """Profile-router registration.

    Hermes discovers this to route domain Q&A here when `finance` is the
    active profile — see spec 014.
    """
    return _PROFILE


@router.post("/bot/assistant", include_in_schema=False)
async def bot_assistant(request: AssistantRequest) -> AssistantResponse:
    """Answer a free-form money question via the conversational assistant.

    `dispatch_path` target for the `finance` profile — Hermes posts here
    instead of running its own devops loop when the question is domain Q&A,
    not a code-change request.
    """
    reply = await assistant_answer(request.chat_id, request.text)
    return AssistantResponse(reply=reply)


@router.get("/bot/ui/finance", include_in_schema=False)
async def bot_finance_ui() -> dict:
    """Initial /finance payload for Hermes' single-bot command surface."""
    return view_payload("balance")


@router.get("/bot/ui/finance/{view}", include_in_schema=False)
async def bot_finance_view(view: str) -> dict:
    """Return a Telegram-ready finance view payload for inline callbacks."""
    return view_payload(view)


@router.get("/bot/ui/finance/spending/{category}", include_in_schema=False)
async def bot_finance_spending_category(category: str) -> dict:
    """Return one spending category drill-down payload."""
    return view_payload("spending_category", category=category)


@router.post("/bot/ui/finance/sync", include_in_schema=False)
async def bot_finance_sync() -> dict:
    """Start sync and return an immediate same-message progress payload."""
    threading.Thread(target=run_sync, daemon=True).start()
    return {
        "text": "🔄 Syncing…",
        "parse_mode": "HTML",
        "reply_markup": balance_keyboard(),
    }
