"""Build the Telegram bot application."""

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from finance_api.domains.bot.commands import BOT_COMMANDS
from finance_api.domains.bot.handlers import (
    BALANCE_CALLBACK,
    INCOME_CALLBACK,
    MONTH_CALLBACK,
    SKIPPED_CALLBACK,
    SPENDING_CALLBACK,
    SPENDING_CAT_PREFIX,
    SUBS_CALLBACK,
    SYNC_CALLBACK,
    balance,
    callback_balance,
    callback_income,
    callback_month,
    callback_skipped,
    callback_spending,
    callback_spending_category,
    callback_subs,
    callback_sync,
    chat,
    cmd_finance_app,
    sync,
)


def create_bot(token: str) -> Application:
    """Create the bot Application with all command handlers registered."""
    app = Application.builder().token(token).build()
    handler_map = {
        "finance_app": cmd_finance_app,
        "finance": balance,
        "balance": balance,
        "sync": sync,
    }
    for command in BOT_COMMANDS:
        if handler := handler_map.get(command.command):
            app.add_handler(CommandHandler(command.command, handler))
    app.add_handler(
        CallbackQueryHandler(callback_balance, pattern=f"^{BALANCE_CALLBACK}(:\\d+)?$")
    )
    app.add_handler(CallbackQueryHandler(callback_sync, pattern=f"^{SYNC_CALLBACK}$"))
    app.add_handler(
        CallbackQueryHandler(callback_income, pattern=f"^{INCOME_CALLBACK}$")
    )
    app.add_handler(
        CallbackQueryHandler(callback_month, pattern=f"^{MONTH_CALLBACK}(:\\d+)?$")
    )
    app.add_handler(
        CallbackQueryHandler(callback_skipped, pattern=f"^{SKIPPED_CALLBACK}$")
    )
    app.add_handler(
        CallbackQueryHandler(
            callback_spending, pattern=f"^{SPENDING_CALLBACK}(:\\d+)?$"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            callback_spending_category,
            pattern=f"^{SPENDING_CAT_PREFIX}",
        )
    )
    app.add_handler(
        CallbackQueryHandler(callback_subs, pattern=f"^{SUBS_CALLBACK}(:\\d+)?$")
    )

    # Catch-all for free-form text — registered last so commands/callbacks above
    # always match first and the existing button UX stays untouched.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    return app
