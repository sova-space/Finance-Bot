# Sova Finance Portal roadmap

This project is the main Sova Space execution lane: a personal finance product Nazar actually uses, with AI and data engineering added only where they improve the workflow.

## Positioning

Sova Finance Portal is an open-source personal finance portal and Telegram operator for seeing the general money picture, controlling spending, and planning next actions.

Not a generic AI chatbot. Not a technology demo.

## Product promise

```text
Bank data + manual context → clean finance model → dashboard → AI explanation → next action
```

## Focus rules

1. Build the useful product first.
2. Use portfolio-grade technology only when it has a real job.
3. Keep private/personal finance data out of public demos.
4. Demo mode must work with synthetic transactions before any public launch.
5. Product Hunt/LinkedIn only after the app is understandable in 30 seconds.

## Main user questions

1. How much money do I have now?
2. Where did money go this month?
3. What changed versus previous period?
4. Which spending is unusual?
5. What should I do next?
6. Are we on track for goals/trips/big expenses?

## MVP finish line

The project is ready to share publicly when it has:

1. deployed web portal;
2. demo dataset with no personal data;
3. balance, spending, budget, and goal views;
4. one useful AI monthly/weekly insight;
5. Telegram summary/notification flow;
6. clear README with architecture and one-command local run;
7. screenshots or short demo video;
8. tests passing in CI.

## Architecture direction

```text
Monobank / manual input / demo data
        ↓
FastAPI backend
        ↓
PostgreSQL operational store
        ↓
analytics queries / future dbt-DuckDB demo layer
        ↓
React + sova-kit portal
        ↓
LLM insights and Telegram summaries
        ↓
Hermes/Sova Brain project reflection, not raw finance storage
```

## AI features that fit

Use LLMs for:

1. monthly summary in plain English/Ukrainian;
2. unusual spending explanation;
3. budget drift explanation;
4. finance Q&A over already-computed facts;
5. next-action suggestions.

Do not use LLMs for:

1. source-of-truth calculations;
2. raw transaction storage;
3. financial advice without deterministic numbers;
4. hallucinated budgets or balances.

## Portfolio technology map

Use now:

- React/Vite + `sova-kit` — portal UI.
- FastAPI — backend/API.
- PostgreSQL — durable app data.
- SQLModel/Alembic — data model and migrations.
- Telegram bot — daily workflow.
- LLM provider — explanation layer.
- Docker/Railway — deployability.
- pytest/ruff/mypy — professional baseline.

Use later only when useful:

- DuckDB/dbt — analytics/demo marts over transactions.
- Airflow — scheduled ingestion/reporting if jobs become complex.
- Kafka — only if event streaming becomes real.
- Spark — only as an isolated scale/demo module with synthetic data, not core MVP.
- LLM evals — regression checks for AI insight quality.

## Public story

Best headline:

> I built a personal finance portal that turns bank transactions into dashboards, AI summaries, and Telegram actions.

Better than:

> I built an AI finance chatbot.

## Near-term priorities

1. Make current portal stable and useful for Nazar.
2. Add demo mode/synthetic seed data.
3. Make AI summary read from deterministic finance facts.
4. Improve README/screenshots.
5. Only then prepare LinkedIn/Product Hunt.
