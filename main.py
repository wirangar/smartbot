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
    weather_handler
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

    # Main conversation handler for user registration and primary interaction
    main_conv_handler = ConversationHandler(
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
                CallbackQueryHandler(user_manager.handle_subscription_callback, pattern=r"^subscribe:.*"),
                CallbackQueryHandler(message_handler.handle_pagination_callback, pattern=r"^pagination:.*"),
                CallbackQueryHandler(feedback_handler.handle_feedback, pattern=r"^feedback:.*"),
                CallbackQueryHandler(menu_handler.handle_action_callback, pattern=r"^action:.*"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler.handle_text_message),
                MessageHandler(filters.VOICE, message_handler.handle_voice_message),
                MessageHandler(filters.Document.ALL, message_handler.handle_file_upload),
                MessageHandler(filters.Document.ALL, message_handler.handle_file_upload),
            ],
        },
        fallbacks=[
            CommandHandler("start", user_manager.start),
            CommandHandler("menu", menu_handler.main_menu_command),
            CommandHandler("profile", user_manager.show_profile_command),
            CommandHandler("subscribe", user_manager.subscribe_command),
            CommandHandler("weather", weather_handler.get_weather),
            CommandHandler("help", menu_handler.help_command),
            CommandHandler("cancel", user_manager.cancel)
        ],
        name="main_conversation",
        persistent=True
    )

    # ISEE conversation handler, can be initiated from the main conversation
    isee_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("isee", isee_handler.start_isee)],
        states={
            isee_handler.INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, isee_handler.handle_income)],
            isee_handler.PROPERTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, isee_handler.handle_property)],
            isee_handler.FAMILY: [MessageHandler(filters.TEXT & ~filters.COMMAND, isee_handler.handle_family)],
            isee_handler.CONFIRM: [CallbackQueryHandler(isee_handler.handle_confirm, pattern=r"^isee_confirm:.*")],
        },
        fallbacks=[CommandHandler("cancel", isee_handler.cancel_isee)],
        # When this conversation ends, it returns to the main menu state of the parent handler
        map_to_parent={
            ConversationHandler.END: user_manager.MAIN_MENU
        }
    )

    # Add handlers to the application
    application.add_handler(main_conv_handler)
    # Note: ISEE handler is now nested conceptually, but needs to be added to the application
    # A better approach might be to add it to the fallbacks of the main handler.
    # For now, this direct addition will work.
    application.add_handler(CommandHandler("isee", isee_handler.start_isee))


    if BASE_URL:
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
