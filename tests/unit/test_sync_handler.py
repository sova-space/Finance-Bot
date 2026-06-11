"""Test that sync work is offloaded via asyncio.to_thread."""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch


async def test_sync_then_edit_calls_run_sync_via_to_thread() -> None:
    """run_sync must be called via asyncio.to_thread, not called directly."""
    from finance_api.domains.bot import handlers
    from finance_api.domains.sync.monobank import run_sync

    message = MagicMock()
    message.edit_text = AsyncMock()

    async def fake_to_thread(fn, *args, **kwargs):
        await asyncio.sleep(0)
        if fn is run_sync:
            return None
        if fn is handlers.get_sync_health:
            return {}
        raise AssertionError(f"unexpected to_thread target: {fn}")

    with (
        patch(
            "finance_api.domains.bot.handlers.asyncio.to_thread",
            side_effect=fake_to_thread,
        ) as mock_to_thread,
        patch("finance_api.domains.bot.handlers.format_sync_status", return_value="ok"),
    ):
        await handlers._sync_then_edit(message)

    assert mock_to_thread.call_args_list[0].args[0] is run_sync
    message.edit_text.assert_awaited_once()


def test_sync_then_edit_source_uses_to_thread() -> None:
    """Static check: background sync source contains 'asyncio.to_thread'."""
    from finance_api.domains.bot.handlers import _sync_then_edit

    assert asyncio.iscoroutinefunction(_sync_then_edit)
    source = inspect.getsource(_sync_then_edit)
    assert "asyncio.to_thread" in source
