# Finance Bot

Track your money automatically from Monobank, control your monthly budget, and plan future goals — with an AI assistant inside Telegram.

Finance Bot is a Telegram-native, Monobank-native personal finance app.

Product structure:

```text
Track → Budget → Plan
        + AI Assistant
```

Technical pipeline:

```text
Ingest → Store → Categorize → Calculate → Explain → Notify
```

See:

- `PRODUCT.md` — product structure and positioning
- `ARCHITECTURE.md` — backend modules, API groups, and open-source path

## Current status

This codebase is currently a single-user/self-hosted finance bot:

- one Telegram bot token
- one Monobank token
- one owner Telegram user id
- one PostgreSQL database

The open-source repo is useful for private self-hosting now. To become a public multi-user bot, it needs the multi-user onboarding and token-storage refactor described in `ARCHITECTURE.md`.

## Features

### Track

- Accounts / cards
- Transactions
- Monobank sync
- Auto-categorization
- Income & expenses
- Recurring bills / subscriptions
- Shared household spending
- Telegram balance and spending summaries

### Budget

- Budgets and category limits
- Fixed/flexible spending foundation
- Alerts and progress foundation
- Pockets system foundation

### Plan

- Goals
- Debts
- Trips
- Buy list
- Forecast
- Expected income / recurring items

### AI Assistant

- Finance Q&A
- Transaction labeling and corrections
- Spending explanation foundation
- Weekly/monthly summary foundation

## Stack

- Python 3.12
- FastAPI
- SQLModel + Alembic
- PostgreSQL
- python-telegram-bot
- APScheduler
- uv
- Railway

## Local development

```bash
uv sync --extra dev
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn finance_api.main:app --reload
```

Tests and lint:

```bash
uv run ruff check finance_api tests
uv run ruff format finance_api tests
uv run pytest tests -q
```

## Environment variables

See `.env.example`.

Required for a private deployment:

- `DATABASE_URL`
- `MONOBANK_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_OWNER_ID`
- `OPENROUTER_API_KEY`
- `MINI_APP_URL`

Optional:

- `TELEGRAM_CHAT_ID` — channel/group/private chat for proactive notifications
- `TELEGRAM_FINANCE_TOPIC_ID` — topic/thread id for forum groups
- `FOP_ACCOUNT_IDS` — comma-separated Monobank account ids to mark as FOP
- `PARTNER_NAME_PATTERN` — regex for partner transfer detection

## Railway deploy

This repo is deployable as one Railway service.

1. Create a PostgreSQL service.
2. Create a Railway service from this GitHub repo.
3. Set env vars in Railway.
4. Deploy.

`entrypoint.sh` runs migrations before starting Gunicorn.

Health check:

```bash
curl https://<your-railway-domain>/health
```

## API groups

Long-term API groups:

```text
/api/accounts
/api/transactions
/api/categories
/api/budgets
/api/planning
/api/insights
/api/telegram
/api/monobank
```

Current implementation still has legacy paths while the standalone product is being extracted.

## Security

Never commit `.env`, bot tokens, Monobank tokens, database URLs, or OpenRouter keys.

If a bot token was pasted into chat or logs, rotate it in BotFather before making the repository public.
