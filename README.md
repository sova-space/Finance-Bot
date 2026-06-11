# Finance Bot

Track money automatically from Monobank, control a monthly budget, and plan future goals — with an AI assistant inside Telegram.

Finance Bot is Monobank-native, Telegram-native, and AI-guided.

## Product shape

```text
Track → Budget → Plan
        + AI Assistant
```

## Tech shape

```text
Ingest → Store → Categorize → Calculate → Explain → Notify
```

`ARCHITECTURE.md` is the source of truth for product mapping, backend modules, API groups, and the open-source/multi-user path.

## Current status

Single-user/self-hosted app:

- one Telegram bot token
- one Monobank token
- one owner Telegram user id
- one PostgreSQL database

Multi-user public bot requires the onboarding/token-storage refactor from `ARCHITECTURE.md`.

## Local development

```bash
uv sync --extra dev
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn finance_api.main:app --reload
```

## Checks

```bash
uv run ruff check finance_api tests
uv run ruff format finance_api tests
uv run pytest tests -q
```

## Deploy

This repo deploys as one Railway service. `entrypoint.sh` runs migrations before Gunicorn.

Required env vars are listed in `.env.example`.

Health check:

```bash
curl https://<railway-domain>/health
```

## Security

Never commit `.env`, bot tokens, Monobank tokens, database URLs, OpenRouter keys, or personal data.

Rotate any token that was pasted into chat/logs before making the repo public.
