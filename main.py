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
from src.handlers import (
    user_manager,
    menu_handler,
    message_handler,
    isee_handler,
    feedback_handler,
    weather_handler,
    search_handler
)
from src.services.notification_service import start_notification_job

async def post_init(application: Application):
    """Post-initialization hook for the application to start background jobs."""
    logger.info("Running post-initialization tasks...")
    asyncio.create_task(start_notification_job(application))

def main() -> None:
    """Run the bot."""
    setup_database()

    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is not set. The bot cannot start.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # --- Independent Conversation Handlers ---
    isee_conv = ConversationHandler(
        entry_points=[
            CommandHandler("isee", isee_handler.start_isee),
            CallbackQueryHandler(isee_handler.start_isee, pattern=r"^isee_start$")
        ],
        states={
            isee_handler.INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, isee_handler.handle_income)],
            isee_handler.PROPERTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, isee_handler.handle_property)],
            isee_handler.FAMILY: [MessageHandler(filters.TEXT & ~filters.COMMAND, isee_handler.handle_family)],
            isee_handler.CONFIRM: [CallbackQueryHandler(isee_handler.handle_confirm, pattern=r"^isee_confirm:.*")],
        },
        fallbacks=[CommandHandler("cancel", isee_handler.cancel_isee)],
        name="isee_conversation",
        persistent=True,
    )

    search_conv = ConversationHandler(
        entry_points=[
            CommandHandler("search", search_handler.start_search),
            CallbackQueryHandler(search_handler.start_search, pattern=r"^search_start$")
        ],
        states={
            search_handler.ASKING_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler.handle_query)],
            search_handler.SHOWING_RESULTS: [
                CallbackQueryHandler(message_handler.handle_pagination_callback, pattern=r"^pagination:.*"),
                CallbackQueryHandler(menu_handler.handle_menu_callback, pattern=r"^menu:.*")
            ]
        },
        fallbacks=[CommandHandler("cancel", search_handler.cancel_search)],
        name="search_conversation",
        persistent=True,
    )

    # --- Main Conversation Handler for Registration and Menu Navigation ---
    main_conv = ConversationHandler(
        entry_points=[CommandHandler("start", user_manager.start)],
        states={
            user_manager.SELECTING_LANG: [CallbackQueryHandler(user_manager.select_language, pattern=r"^lang:.*")],
            user_manager.ASKING_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_manager.ask_first_name)],
            user_manager.ASKING_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_manager.ask_last_name)],
            user_manager.ASKING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_manager.ask_age)],
            user_manager.ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_manager.ask_email)],
            user_manager.MAIN_MENU: [
                CallbackQueryHandler(menu_handler.handle_menu_callback, pattern=r"^menu:.*"),
            ],
        },
        fallbacks=[CommandHandler("cancel", user_manager.cancel)],
        name="main_menu_conversation",
        persistent=True,
    )

    # Add all handlers to the application
    application.add_handler(main_conv)
    application.add_handler(isee_conv)
    application.add_handler(search_conv)

    # Add handlers for commands that can be used at any time
    application.add_handler(CommandHandler("weather", weather_handler.get_weather))
    application.add_handler(CommandHandler("help", menu_handler.help_command))
    application.add_handler(CommandHandler("profile", user_manager.show_profile_command))
    application.add_handler(CommandHandler("subscribe", user_manager.subscribe_command))

    # Add handlers for callbacks that are not part of a conversation
    application.add_handler(CallbackQueryHandler(feedback_handler.handle_feedback, pattern=r"^feedback:.*"))
    application.add_handler(CallbackQueryHandler(user_manager.handle_subscription_callback, pattern=r"^subscribe:.*"))

    # Add handlers for messages
    application.add_handler(MessageHandler(filters.VOICE, message_handler.handle_voice_message))
    application.add_handler(MessageHandler(filters.Document.ALL, message_handler.handle_file_upload))
    # This should be the last handler to act as a fallback for non-command text
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler.handle_text_message))


    if BASE_URL:
        logger.info(f"Starting bot in webhook mode, listening on port {PORT}")
        application.run_webhook(listen="0.0.0.0", port=PORT, secret_token=WEBHOOK_SECRET, url_path=TELEGRAM_BOT_TOKEN, webhook_url=f"{BASE_URL}/{TELEGRAM_BOT_TOKEN}")
    else:
        logger.info("No BASE_URL found, running in polling mode for local development.")
        application.run_polling()

if __name__ == "__main__":
    main()
