# Finance Bot

Track money automatically from Monobank, control a monthly budget, and plan future goals — with an AI assistant inside Telegram.

Finance Bot is Monobank-native, Telegram-native, and AI-guided.

## Documentation

- [Architecture](docs/architecture.md) — product mapping, backend modules, API groups, open-source path.
- [BotFather setup](docs/botfather.md) — group privacy and Telegram-side bot settings.

## Product shape

```text
Track → Budget → Plan
        + AI Assistant
```

## Tech shape

```text
Ingest → Store → Categorize → Calculate → Explain → Notify
```

`docs/architecture.md` is the source of truth for architecture.

## Current status

Single-user/self-hosted app:

- one Telegram bot token
- one Monobank token
- one owner Telegram user id
- one PostgreSQL database

Multi-user public bot requires the onboarding/token-storage refactor from `docs/architecture.md`.

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

## Telegram group setup

For LLM replies in groups, disable bot privacy in BotFather:

`@BotFather` → `/mybots` → `@sova_finance_bot` → `Bot Settings` → `Group Privacy` → `Turn off`

Details: [BotFather setup](docs/botfather.md).

## Package layout

Keep the Python package as `finance_api` for now. It is explicit, already wired through imports, Alembic, Docker, Gunicorn, tests, and deployment.

Do not rename it to `src`. If we want a `src/` layout later, use `src/finance_api`, not package name `src`.

## Security

Never commit `.env`, bot tokens, Monobank tokens, database URLs, OpenRouter keys, or personal data.

Rotate any token that was pasted into chat/logs before making the repo public.
