import logging
import json
from pathlib import Path
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from src.config import logger, TELEGRAM_BOT_TOKEN, BASE_URL, PORT, WEBHOOK_SECRET, OPENWEATHERMAP_API_KEY, MissingEnvVarError
from src.handlers.user_manager import (
    start,
    select_language,
    ask_first_name,
    ask_last_name,
    ask_age,
    ask_email,
    cancel,
    show_profile_command,
    SELECTING_LANG, ASKING_FIRST_NAME, ASKING_LAST_NAME, ASKING_AGE, ASKING_EMAIL, MAIN_MENU
)
from src.handlers.menu_handler import main_menu_command, help_command, handle_menu_callback, handle_action_callback, handle_pagination
from src.handlers.message_handler import handle_text_message, handle_voice_message
from src.database import initialize_connections, get_db_cursor
from src.services.isee_service import ISEEService
from src.services.search_engine import SearchEngine
from src.utils.paginator import Paginator
from src.utils.text_formatter import sanitize_markdown
from src.utils.keyboard_builder import get_main_menu_keyboard
from src.data.knowledge_base import get_knowledge_base

def setup_application() -> Application:
    """Initialize and configure the Telegram application."""
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is not configured.")
        raise ValueError("TELEGRAM_BOT_TOKEN is missing.")

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(10)
        .write_timeout(10)
        .build()
    )

    knowledge_base = get_knowledge_base()
    application.bot_data['knowledge_base'] = knowledge_base
    application.bot_data['db_manager'] = None  # Placeholder
    application.bot_data['OPENWEATHERMAP_API_KEY'] = OPENWEATHERMAP_API_KEY

    return application


def setup_handlers(application: Application):
    """Set up the conversation and error handlers."""
    isee_service = ISEEService(application.bot_data['knowledge_base'], None)
    search_engine = SearchEngine(Paginator())

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", main_menu_command),
            CommandHandler("help", help_command),
            CommandHandler("profile", show_profile_command),
            isee_service.get_conversation_handler().entry_points[0]
        ],
        states={
            SELECTING_LANG: [CallbackQueryHandler(select_language, pattern="^lang:")],
            ASKING_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_first_name)],
            ASKING_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_last_name)],
            ASKING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            MAIN_MENU: [
                CommandHandler("menu", main_menu_command),
                CommandHandler("help", help_command),
                CommandHandler("profile", show_profile_command),
                CallbackQueryHandler(handle_menu_callback, pattern="^menu:"),
                CallbackQueryHandler(handle_action_callback, pattern="^action:"),
                CallbackQueryHandler(handle_pagination, pattern="^pagination:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message),
                MessageHandler(filters.VOICE, handle_voice_message),
                search_engine.get_handler()
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    async def error_handler(update, context):
        """Log Errors caused by Updates."""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            lang = context.user_data.get('language', 'fa') if context.user_data else 'fa'
            error_message = f"An error occurred: {context.error}"
            if lang == 'fa':
                error_message = f"یک خطا رخ داد: {context.error}"
            elif lang == 'it':
                error_message = f"Si è verificato un errore: {context.error}"

            await update.effective_message.reply_text(sanitize_markdown(error_message))

    application.add_error_handler(error_handler)


async def run_webhook(application: Application):
    """Set up and run the webhook."""
    webhook_url = f"{BASE_URL}/webhook"
    try:
        await application.initialize()
        await application.bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=["message", "callback_query"]
        )
        logger.info(f"Webhook set successfully at {webhook_url}")

        await application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            secret_token=WEBHOOK_SECRET,
            webhook_url=webhook_url
        )
    except Exception as e:
        logger.critical(f"Failed to start webhook: {e}")
        raise


async def main():
    """Run the bot."""
    try:
        initialize_connections()
        application = setup_application()
        setup_handlers(application)
        await run_webhook(application)
    except (ValueError, MissingEnvVarError) as e:
        logger.critical(f"Initialization failed: {e}")
    except Exception as e:
        logger.critical(f"An unexpected error occurred during startup: {e}")

if __name__ == "__main__":
    import asyncio
    import os
    asyncio.run(main())
