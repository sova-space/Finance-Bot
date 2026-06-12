# BotFather setup

Use BotFather for Telegram-side bot settings.

## Group LLM replies

To let the finance assistant read normal group messages, disable bot privacy:

1. Open `@BotFather`.
2. Send `/mybots`.
3. Select `@sova_finance_bot`.
4. Open `Bot Settings`.
5. Open `Group Privacy`.
6. Select `Turn off`.
7. Remove the bot from the group and add it again if Telegram does not apply the change immediately.

With privacy disabled, the app answers plain text from `TELEGRAM_OWNER_ID` in any group topic. It ignores messages from other users. Mentions like `@sova_finance_bot` still work and are stripped before sending the prompt to the LLM.

## Commands

Commands are registered by the app at startup from `finance_api/domains/bot/commands.py`.
