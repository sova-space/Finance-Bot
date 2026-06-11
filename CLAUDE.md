# Finance Bot

Telegram-native, Monobank-native personal finance app.

## Product

User-facing structure:

- Track
- Budget
- Plan
- AI Assistant across everything

Technical pipeline:

- Ingest
- Store
- Categorize
- Calculate
- Explain
- Notify

See `PRODUCT.md` and `ARCHITECTURE.md`.

## Repo structure

```text
finance_api/   — FastAPI app
  domains/     — business domains
  routers/     — HTTP API routers
alembic/       — DB migrations
tests/         — pytest tests
```

## Guardrails

- Never commit secrets, tokens, database URLs, `.env`, or personal data.
- Keep this repo self-hostable and open-source friendly.
- Required config should fail loud unless explicitly optional.
- Current app is single-user; multi-user SaaS requires the `ARCHITECTURE.md` refactor first.
- Use Python 3.12+, uv, ruff, pytest.

## Workflow

```bash
uv run ruff check finance_api tests
uv run ruff format finance_api tests
uv run pytest tests -q
```

Deploy verified changes from `main`.
