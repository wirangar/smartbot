import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.config import logger
from src.database import get_db_cursor
from src.locale import get_message

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves user feedback to the database."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = context.user_data.get('language', 'fa')

    try:
        _, choice, message_id = query.data.split(":")
        is_helpful = True if choice == 'yes' else False

        # In a more advanced version, we could retrieve the original message text
        # using the message_id and store it for context.
        original_message = f"Feedback for message ID: {message_id}"

        with get_db_cursor() as cursor:
            cursor.execute(
                "INSERT INTO feedback (user_id, is_helpful, message_text) VALUES (%s, %s, %s)",
                (user_id, is_helpful, original_message)
            )

        # Edit the original message to remove the feedback buttons
        await query.edit_message_reply_markup(reply_markup=None)
        # Send a new message to confirm feedback was received
        await context.bot.send_message(chat_id=user_id, text=get_message("feedback_thanks", lang))

    except Exception as e:
        logger.error(f"Error handling feedback for user {user_id}: {e}")
        # Silently fail to not disrupt user flow, but log the error.
        pass
