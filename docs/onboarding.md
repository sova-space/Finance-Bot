# Onboarding guide

This project has two onboarding modes:

1. Self-hosted onboarding — works now.
2. Public multi-user onboarding — product direction, not implemented yet.

## 1. Self-hosted onboarding

Use this when someone wants their own private Finance Bot deployment.

### User needs

- Telegram bot from BotFather
- Monobank personal token
- PostgreSQL database
- OpenRouter API key
- Railway account or another Docker host

### Steps

1. Fork or clone the repo.
2. Copy mock env values:

```bash
cp .env.mock .env
```

3. Replace mock values in `.env`:

```text
DATABASE_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_ID=
MONOBANK_TOKEN=
OPENROUTER_API_KEY=
MINI_APP_URL=
```

4. Run locally:

```bash
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn finance_api.main:app --reload
```

5. Open Telegram and send:

```text
/sync
/balance
```

### Railway setup

1. Create PostgreSQL service.
2. Create app service from this repo.
3. Set variables from `.env.mock` with real values.
4. Generate Railway domain.
5. Set:

```text
MINI_APP_URL=https://<railway-domain>/miniapp
```

6. Deploy.
7. Check:

```bash
curl https://<railway-domain>/health
```

## Telegram setup

BotFather:

1. Create bot.
2. Set commands from app startup or manually if needed.
3. For group/topic usage, disable privacy:

```text
/mybots → <bot> → Bot Settings → Group Privacy → Turn off
```

4. Add bot to the group.
5. If privacy was changed after adding the bot, remove and add the bot again.

The app answers plain text only from `TELEGRAM_OWNER_ID`; other users are ignored in the current single-user mode.

## 2. Public multi-user onboarding

This is the target for letting other people use one hosted bot without deploying their own instance.

### Target user flow

```text
/start
→ choose language
→ paste Monobank token
→ validate token
→ first sync
→ show Balance
```

### Required backend changes

- Add `users` table.
- Store `telegram_user_id`.
- Store encrypted `monobank_token` per user.
- Scope accounts, transactions, budgets, rules, goals, trips, and settings by `user_id`.
- Replace global `TELEGRAM_OWNER_ID` gate with registered-user access.
- Replace global `MONOBANK_TOKEN` with per-user token lookup.
- Add `/delete_my_data`.
- Add export path.
- Add privacy policy.

### Token storage rule

Never store Monobank tokens as plain text.

Use server-side encryption:

```text
encrypted_token = encrypt(monobank_token, APP_SECRET)
```

`APP_SECRET` must be a Railway/host env var and must never be committed.

### Minimal first public version

Do not build teams, billing, roles, or advanced permissions first.

Build only:

- `/start`
- token save/validate
- first sync
- balance/spending views scoped by user
- delete my data
- privacy policy

Keep self-hosted mode working for people who prefer private deployments.
