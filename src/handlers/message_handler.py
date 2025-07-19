from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import logging

from services.openai_service import get_ai_response
from services.google_sheets import append_qa_to_sheet
from utils.keyboard_builder import get_main_keyboard_markup
from handlers.start_handler import MAIN_MENU

logger = logging.getLogger(__name__)

from src.config import ADMIN_CHAT_ID

async def handle_free_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_message = update.message.text
    user = update.effective_user
    logger.info(f"Received free text message from user {user.id}: '{user_message}'")

    # Check if this message is for the admin
    if context.user_data.get('next_message_is_admin_contact'):
        context.user_data['next_message_is_admin_contact'] = False
        if ADMIN_CHAT_ID:
            try:
                await context.bot.forward_message(chat_id=ADMIN_CHAT_ID, from_chat_id=user.id, message_id=update.message.message_id)
                await update.message.reply_text("پیام شما با موفقیت برای ادمین ارسال شد. منتظر پاسخ بمانید.")
            except Exception as e:
                logger.error(f"Failed to forward message to admin: {e}")
                await update.message.reply_text("متاسفانه در ارسال پیام به ادمین خطایی رخ داد.")
        else:
            await update.message.reply_text("قابلیت تماس با ادمین در حال حاضر فعال نیست.")

        return MAIN_MENU

    # Otherwise, process with OpenAI
    ai_response = await get_ai_response(user_message)

    if ai_response:
        # Personalize response
        first_name = context.user_data.get('first_name', 'کاربر')
        final_response = f"{first_name} عزیز، این پاسخ برای شماست:\n\n{ai_response}"
        await append_qa_to_sheet(user.id, user_message, ai_response)
    else:
        final_response = "متاسفم، در حال حاضر قادر به پاسخگویی با هوش مصنوعی نیستم. لطفاً از منوهای موجود استفاده کنید."

    await update.message.reply_text(
        final_response,
        reply_markup=get_main_keyboard_markup(context.user_data.get('current_path', []))
    )

    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "من فقط در مورد بورسیه‌های دانشجویی و زندگی در شهر پروجا می‌تونم کمکت کنم. سوالاتت رو در این مورد بپرس یا از منو استفاده کن.",
        reply_markup=get_main_keyboard_markup(context.user_data.get('current_json_path', []))
    )
