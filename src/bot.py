import asyncio
import logging
from flask import Request
from functions_framework import http
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)

# Import configurations and handlers from the new modular structure
from src.config import TELEGRAM_BOT_TOKEN, WEBHOOK_SECRET, BASE_URL, logger
from src.handlers.start_handler import (
    start, ask_first_name, ask_last_name, ask_age, ask_email, cancel,
    ASKING_FIRST_NAME, ASKING_LAST_NAME, ASKING_AGE, ASKING_EMAIL, MAIN_MENU
)
from src.handlers.menu_handler import handle_json_menu_callback, handle_action_callback
from src.handlers.message_handler import handle_free_text_message, help_command

# --- Initialize Application ---
# Ensure the token is available
if not TELEGRAM_BOT_TOKEN:
    logger.critical("TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
    exit()

application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# --- Conversation Handler Setup ---
# This handler manages the user registration flow and the main menu interactions.
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASKING_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_first_name)],
        ASKING_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_last_name)],
        ASKING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
        ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
        MAIN_MENU: [
            CallbackQueryHandler(handle_json_menu_callback, pattern=r"^json_menu:.*"),
            CallbackQueryHandler(handle_action_callback, pattern=r"^action:.*"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text_message),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    # Allow re-entry into the conversation with the /start command
    allow_reentry=True,
)

# Add handlers to the application
application.add_handler(conv_handler)
application.add_handler(CommandHandler("help", help_command))

# --- Webhook Setup ---
# This part is for deploying on a serverless platform like Google Cloud Functions or Render.
# It uses an HTTP trigger to process updates.

# The asyncio event loop is necessary for python-telegram-bot's async operations.
loop = asyncio.get_event_loop()
if loop.is_closed():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

@http
def telegram_webhook(request: Request):
    """HTTP-triggered function that processes a single Telegram update."""
    if request.method == "POST":
        update_json = request.get_json()
        update = Update.de_json(update_json, application.bot)

        # Running the async processing in the existing event loop
        asyncio.run_coroutine_threadsafe(application.process_update(update), loop)

        return "", 200
    return "Invalid request", 400

async def set_webhook():
    """Sets the Telegram webhook URL."""
    webhook_url = f"{BASE_URL}/{TELEGRAM_BOT_TOKEN}"
    logger.info(f"Setting webhook to: {webhook_url}")
    try:
        await application.bot.set_webhook(url=webhook_url, secret_token=WEBHOOK_SECRET)
        logger.info("Webhook set successfully.")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

# --- Main Execution ---
# This block is for local development (polling) and to set the webhook for production.
if __name__ == "__main__":
    # In a production environment (like Render), we might just want to set the webhook.
    # The server (like Gunicorn) would run the `telegram_webhook` function.
    if BASE_URL:
        loop.run_until_complete(set_webhook())
    else:
        # For local development, run the bot in polling mode.
        logger.info("BASE_URL not found. Running in polling mode for local development.")
        application.run_polling()
