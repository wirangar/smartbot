from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import logging

from src.services.openai_service import get_ai_response
from src.services.google_sheets import append_qa_to_sheet
from src.utils.keyboard_builder import get_main_keyboard_markup
from src.handlers.start_handler import MAIN_MENU

logger = logging.getLogger(__name__)

async def handle_free_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_message = update.message.text
    user_id = update.effective_user.id
    logger.info(f"Received free text message from user {user_id}: '{user_message}'")

    ai_response = await get_ai_response(user_message)

    if ai_response:
        first_name = context.user_data.get('first_name')
        age = context.user_data.get('age')

        # Personalize response
        if first_name and age:
            final_response = f"{first_name} عزیز ({age} ساله)، این پاسخ برای شماست:\n\n{ai_response}"
        elif first_name:
            final_response = f"{first_name} عزیز، این پاسخ برای شماست:\n\n{ai_response}"
        else:
            final_response = ai_response

        await append_qa_to_sheet(user_id, user_message, ai_response)
    else:
        final_response = "متاسفم، در حال حاضر قادر به پاسخگویی با هوش مصنوعی نیستم. لطفاً کمی بعدتر دوباره امتحان کنید یا از منوهای موجود استفاده کنید."

    await update.message.reply_text(
        final_response,
        reply_markup=get_main_keyboard_markup(context.user_data.get('current_json_path', []))
    )

    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "من فقط در مورد بورسیه‌های دانشجویی و زندگی در شهر پروجا می‌تونم کمکت کنم. سوالاتت رو در این مورد بپرس یا از منو استفاده کن.",
        reply_markup=get_main_keyboard_markup(context.user_data.get('current_json_path', []))
    )
