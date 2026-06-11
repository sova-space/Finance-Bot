# Product Structure

## Positioning

Track your money automatically from Monobank, control your monthly budget, and plan future goals — with an AI assistant inside Telegram.

## Core product

Finance Bot is a Telegram + Monobank personal finance app.

User-facing structure:

```text
Personal Finance App
├── 1. Track
├── 2. Budget
├── 3. Plan
└── AI Assistant across everything
```

Short version:

```text
Track → Budget → Plan
        + AI Assistant
```

## 1. Track

Track is the source of truth for money movement.

Includes:

- Accounts / cards
- Transactions
- Auto-categorization
- Recurring bills
- Income & expenses
- Shared household spending
- Telegram dashboard / summary

User outcome:

“I always know what happened with my money.”

## 2. Budget

Budget is the control layer.

Includes:

- Budget method
  - Simple budget
  - Flex budgeting
  - Category budgeting
- Categories & groups
- Fixed expenses
- Flexible expenses
- Non-monthly expenses
- Shared household budget
- Alerts & progress

User outcome:

“I know if I’m safe this month and where I can spend.”

## 3. Plan

Plan is the future layer.

Includes:

- Goals
- Monthly contributions
- Cashflow forecast
- Debt payoff
- Savings targets
- Future expenses
- Progress tracking

User outcome:

“I know what I can afford later and how to reach goals.”

## AI Assistant

The assistant works across Track, Budget, and Plan.

Includes:

- Explains spending changes
- Detects trends
- Suggests next actions
- Answers finance questions
- Improves categorization
- Creates weekly / monthly summaries

User outcome:

“I don’t need to inspect reports manually — the bot explains what matters.”

## Differentiation

Monarch is app-first.

Finance Bot is:

- Monobank-native
- Telegram-native
- AI-guided
- Lightweight and chat-first
- Self-hostable first, SaaS-capable later
