import asyncio
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)

from src.config import TELEGRAM_BOT_TOKEN, WEBHOOK_SECRET, BASE_URL, PORT, logger
from src.database import setup_database
from src.handlers import user_manager, menu_handler, message_handler

def main() -> None:
    """Run the bot."""
    # Set up the database tables on startup
    setup_database()

    # Create the Application and pass it your bot's token.
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is not set. The bot cannot start.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Setup the conversation handler with states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", user_manager.start)],
        states={
            user_manager.SELECTING_LANG: [CallbackQueryHandler(user_manager.select_language, pattern=r"^lang:.*")],
            user_manager.ASKING_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_manager.ask_first_name)],
            user_manager.ASKING_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_manager.ask_last_name)],
            user_manager.ASKING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_manager.ask_age)],
            user_manager.ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_manager.ask_email)],
            user_manager.MAIN_MENU: [
                CallbackQueryHandler(menu_handler.handle_menu_callback, pattern=r"^menu:.*"),
                CallbackQueryHandler(user_manager.show_profile, pattern=r"^action:profile$"),
                CallbackQueryHandler(menu_handler.handle_action_callback, pattern=r"^action:.*"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler.handle_text_message),
                MessageHandler(filters.VOICE, message_handler.handle_voice_message),
            ],
        },
        fallbacks=[CommandHandler("cancel", user_manager.cancel)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)

    # For local development, run via polling
    # For production on Render, the webhook is set via a startup command
    if BASE_URL:
        # On Render, you would typically run a webserver.
        # For simplicity with python-telegram-bot, we can run it in webhook mode.
        logger.info(f"Starting bot in webhook mode, listening on port {PORT}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            secret_token=WEBHOOK_SECRET,
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=f"{BASE_URL}/{TELEGRAM_BOT_TOKEN}"
        )
    else:
        logger.info("No BASE_URL found, running in polling mode for local development.")
        application.run_polling()


if __name__ == "__main__":
    main()
