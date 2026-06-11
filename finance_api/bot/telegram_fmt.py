"""Shared Telegram HTML formatting helpers. No finance logic here."""

from telegram.constants import ParseMode

PARSE_MODE = ParseMode.HTML
DIVIDER = "─" * 16


def bold(text: str) -> str:
    """Wrap text in HTML bold tags."""
    return f"<b>{text}</b>"


def italic(text: str) -> str:
    """Wrap text in HTML italic tags."""
    return f"<i>{text}</i>"


def escape(text: str) -> str:
    """Escape HTML special characters for safe inclusion in HTML messages."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def code(text: str) -> str:
    """Wrap text in HTML code tags — escapes content automatically."""
    return f"<code>{escape(str(text))}</code>"


def blockquote(text: str) -> str:
    """Wrap text in a blockquote — renders as a blue row in Telegram."""
    return f"<blockquote>{text}</blockquote>"


def pre(text: str) -> str:
    """Wrap text in a pre block — renders as a monospace code box in Telegram."""
    return f"<pre>{text}</pre>"


def expandable_blockquote(text: str) -> str:
    """Wrap text in a collapsible blockquote — user taps to expand."""
    return f"<blockquote expandable>{text}</blockquote>"
