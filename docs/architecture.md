# Technical Architecture

Product structure:

```text
Track → Budget → Plan
        + AI Assistant
```

Technical pipeline:

```text
Ingest → Store → Categorize → Calculate → Explain → Notify
```

## Product-to-tech mapping

| Product area | Technical system |
|---|---|
| Track | Monobank sync, transactions, accounts, categories |
| Budget | Budget engine, limits, fixed/flexible spending |
| Plan | Goals, cashflow forecast, future expenses |
| AI Assistant | LLM insights, trend detection, Q&A, summaries |
| Telegram Summary | Bot API, notifications, scheduled messages |

## Backend modules

Keep the import package named `finance_api`. It is explicit and already wired through imports, Alembic, Docker, Gunicorn, tests, and deploy config. Do not rename the package to `src`; if this repo later adopts a `src/` layout, use `src/finance_api`.

Current code lives under `finance_api/`. The long-term domain structure should converge to:

```text
finance_api
├── monobank
│   ├── sync
│   ├── webhook / polling
│   └── account linking
│
├── transactions
│   ├── transaction storage
│   ├── deduplication
│   ├── merchant detection
│   └── income / expense / transfer detection
│
├── categories
│   ├── default categories
│   ├── category rules
│   ├── AI categorization
│   └── user corrections
│
├── budgets
│   ├── monthly budget
│   ├── category limits
│   ├── fixed expenses
│   ├── flexible expenses
│   └── alerts
│
├── planning
│   ├── goals
│   ├── future expenses
│   ├── cashflow forecast
│   └── savings progress
│
├── insights
│   ├── weekly summary
│   ├── monthly review
│   ├── spending changes
│   ├── trend detection
│   └── AI Q&A
│
└── telegram
    ├── commands
    ├── buttons
    ├── notifications
    └── household chats
```

## Recommended API groups

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

Current API paths may differ. Do not rename everything at once. Migrate gradually when touching a domain.

## Open-source path

Current app is single-user/self-hosted:

- one `MONOBANK_TOKEN`
- one `TELEGRAM_BOT_TOKEN`
- one `TELEGRAM_OWNER_ID`
- one database tenant

Before public SaaS usage, change to multi-user:

1. Add users table.
2. Store Monobank token per user, encrypted at rest.
3. Scope accounts, transactions, budgets, goals, trips, and rules by `user_id`.
4. Replace `TELEGRAM_OWNER_ID` hard gate with registered-user access.
5. Add `/start` onboarding and Monobank token linking.
6. Add `/delete_my_data` and export path.
7. Add privacy policy and security docs.
8. Keep self-host mode via env vars for private deployments.

## Deployment model

Phase 1 — private standalone deployment:

- separate GitHub repo
- separate Railway service
- separate PostgreSQL database
- one Telegram bot token
- one owner

Phase 2 — public self-hosted project:

- documented env vars
- Railway template
- no personal defaults
- seed demo rules/categories only

Phase 3 — multi-user hosted product:

- onboarding
- per-user token storage
- tenant isolation
- billing/subscription if needed
