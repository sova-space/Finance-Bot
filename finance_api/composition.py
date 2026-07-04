"""FastAPI application factory."""

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from finance_api.core.config import settings
from finance_api.core.logging.setup import configure_logging
from finance_api.domains.bot.notifications import (
    send_notification,
    set_notification_context,
)
from finance_api.domains.pockets.jobs import reset_pockets_job
from finance_api.domains.sync.monobank import run_sync
from finance_api.routers import (
    accounts,
    budgets,
    buy_list,
    dashboard,
    debts,
    fx,
    goals,
    health,
    pockets,
    sync,
    transactions,
    trips,
)
from finance_api.routers import operator as operator_router
from finance_api.routers.forecast import (
    forecast_router,
    income_router,
    recurring_router,
)

log = structlog.get_logger(__name__)


def _send_daily_statistics() -> None:
    from finance_api.domains.insights.queries import (
        format_statistics_report,
        get_daily_statistics,
    )

    send_notification(
        format_statistics_report(get_daily_statistics()),
        thread_id=settings.telegram_finance_topic_id,
    )


def _send_month_statistics() -> None:
    from finance_api.domains.insights.queries import (
        format_statistics_report,
        get_month_statistics,
    )

    send_notification(
        format_statistics_report(get_month_statistics()),
        thread_id=settings.telegram_finance_topic_id,
    )


_DESCRIPTION = """
Finance API — a thin wrapper around Monobank that syncs your bank data to
PostgreSQL and exposes read-only analytics endpoints.

## Integration endpoints

| Goal | Endpoint |
|---|---|
| Account balances | `GET /accounts` |
| Spending by category | `GET /transactions/spending?period=this_month` |
| Exclude bank transfers | `GET /transactions/spending?exclude_uncategorized=true` |
| Monthly income/expense trend | `GET /transactions/trend?months=3` |
| Recent transactions | `GET /transactions?limit=20` |
| Trigger a sync | `POST /sync` |
| Last sync status | `GET /sync/status` |
| Budget limits + spending | `GET /budgets` |
| Set a budget limit | `POST /budgets` |
| Remove a budget limit | `DELETE /budgets/{category}` |

## Periods

`this_month` · `last_month` · `last_7d` · `last_30d` · `last_90d`

## Account filtering

All transaction endpoints accept `?account_id=<uuid>` to scope results to one account.
"""


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging(
        level=settings.log_level,
        json=settings.environment != "local",
    )

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_sync,
        "interval",
        hours=settings.sync_interval_hours,
        id="monobank_sync",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        reset_pockets_job,
        trigger=CronTrigger(day=1, hour=0, minute=5),
        id="pocket_monthly_reset",
        replace_existing=True,
    )
    scheduler.add_job(
        _send_daily_statistics,
        trigger=CronTrigger(hour=22, minute=0),
        id="daily_statistics",
        replace_existing=True,
    )
    scheduler.add_job(
        _send_month_statistics,
        trigger=CronTrigger(day="last", hour=22, minute=5),
        id="month_statistics",
        replace_existing=True,
    )

    bot_app = None
    telegram_polling_enabled = os.getenv("FINANCE_SERVICE_ROLE", "all") != "core"
    if settings.telegram_bot_token and telegram_polling_enabled:
        from finance_api.domains.bot.runner import create_bot

        bot_app = create_bot(settings.telegram_bot_token)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        scheduler.start()
        log.info("scheduler_started", interval_hours=settings.sync_interval_hours)
        if bot_app:
            from finance_api.domains.bot.commands import setup_bot

            await bot_app.initialize()
            await setup_bot(bot_app.bot)
            await bot_app.start()
            await bot_app.updater.start_polling(drop_pending_updates=True)
            log.info("telegram_bot_started")
            loop = asyncio.get_event_loop()
            set_notification_context(bot_app, loop)
        try:
            yield
        finally:
            scheduler.shutdown(wait=False)
            if bot_app:
                await bot_app.updater.stop()
                await bot_app.stop()
                await bot_app.shutdown()

    app = FastAPI(
        title="Finance API",
        version="0.1.0",
        description=_DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(health.router, tags=["health"])
    app.include_router(operator_router.router, tags=["operator"])
    app.include_router(dashboard.router, tags=["dashboard"])

    dashboard_assets_dir = Path(__file__).parent / "static" / "app" / "assets"
    if dashboard_assets_dir.exists():
        app.mount(
            "/app/assets",
            StaticFiles(directory=dashboard_assets_dir),
            name="dashboard-assets",
        )

    app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
    app.include_router(fx.router)
    app.include_router(
        transactions.router,
        prefix="/transactions",
        tags=["transactions"],
    )
    app.include_router(sync.router, prefix="/sync", tags=["sync"])
    app.include_router(budgets.router, prefix="/budgets", tags=["budgets"])
    app.include_router(debts.router)
    app.include_router(goals.router)
    app.include_router(trips.router)
    app.include_router(buy_list.router)
    app.include_router(forecast_router)
    app.include_router(recurring_router)
    app.include_router(income_router)
    app.include_router(pockets.router)

    return app
