from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import logging

from src.utils.keyboard_builder import get_main_keyboard_markup
from src.data.knowledge_base import get_json_content_by_path
from src.services.google_sheets import get_previous_answers
from src.handlers.start_handler import MAIN_MENU

logger = logging.getLogger(__name__)

async def handle_json_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    path_indicator = data[1] if len(data) > 1 else ""

    if path_indicator == "main_menu":
        context.user_data['current_json_path'] = []
    else:
        context.user_data['current_json_path'] = data[1:]

    current_path_parts = context.user_data.get('current_json_path', [])
    content_to_display = get_json_content_by_path(current_path_parts)

    keyboard = get_main_keyboard_markup(current_path_parts)

    if content_to_display:
        await query.edit_message_text(content_to_display, reply_markup=keyboard)
    else:
        message_text = "لطفاً یک گزینه را انتخاب کنید:"
        if not current_path_parts:
            message_text = "شما در منوی اصلی هستید. لطفاً یک دسته را انتخاب کنید یا سوال خود را مطرح کنید:"
        await query.edit_message_text(message_text, reply_markup=keyboard)

    return MAIN_MENU

async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1]

    user_path = context.user_data.get('current_json_path', [])
    keyboard = get_main_keyboard_markup(user_path)

    if action == "new_question":
        await query.edit_message_text(
            "لطفاً سوال جدید خود را مطرح کنید. من تلاش می‌کنم با هوش مصنوعی به آن پاسخ دهم.\n"
            "برای بازگشت به منوها می‌توانید از دکمه‌های زیر استفاده کنید.",
            reply_markup=keyboard
        )
    elif action == "previous_answers":
        telegram_id = update.effective_user.id
        previous_answers = await get_previous_answers(telegram_id)
        await query.edit_message_text(previous_answers, reply_markup=keyboard)
    elif action == "help":
        help_text = (
            "من یک ربات هوش مصنوعی هستم که در مورد بورسیه‌های دانشجویی و زندگی در شهر پروجا ایتالیا به شما کمک می‌کنم.\n"
            "می‌توانید با استفاده از دکمه‌های منو اطلاعات مورد نظرتان را پیدا کنید، یا سوال خود را به صورت متنی مطرح کنید تا من با هوش مصنوعی پاسخ دهم."
        )
        await query.edit_message_text(help_text, reply_markup=keyboard)

    return MAIN_MENU
