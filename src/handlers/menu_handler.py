from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import logging

from utils.keyboard_builder import get_main_keyboard_markup
from data.knowledge_base import get_json_content_by_path
from services.google_sheets import get_previous_answers
from handlers.start_handler import MAIN_MENU

logger = logging.getLogger(__name__)

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    path_indicator = data[1] if len(data) > 1 else "main_menu"

    if path_indicator == "main_menu":
        context.user_data['current_path'] = []
        message_text = "شما در منوی اصلی هستید. لطفاً یک دسته را انتخاب کنید:"
        keyboard = get_main_keyboard_markup([])
        await query.edit_message_text(message_text, reply_markup=keyboard)
    else:
        path_parts = data[1:]
        context.user_data['current_path'] = path_parts

        content_to_display = get_json_content_by_path(path_parts)
        keyboard = get_main_keyboard_markup(path_parts)

        if len(path_parts) == 1: # Category level
            await query.edit_message_text("لطفا یک مورد را انتخاب کنید:", reply_markup=keyboard)
        elif len(path_parts) > 1: # Item level
            await query.edit_message_text(content_to_display, reply_markup=keyboard, parse_mode='Markdown')

    return MAIN_MENU

async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1]

    user_path = context.user_data.get('current_path', [])
    keyboard = get_main_keyboard_markup(user_path)

    if action == "contact_admin":
        context.user_data['next_message_is_admin_contact'] = True
        await query.edit_message_text(
            "لطفاً پیام خود را برای ارسال به ادمین تایپ کنید. پیام شما مستقیماً به ادمین ارسال خواهد شد.",
            reply_markup=keyboard
        )
    elif action == "previous_answers":
        telegram_id = update.effective_user.id
        previous_answers = await get_previous_answers(telegram_id)
        await query.edit_message_text(previous_answers, reply_markup=keyboard)
    elif action == "help":
        help_text = (
            "این ربات برای راهنمایی دانشجویان در پروجا طراحی شده است.\n"
            "- از منوها برای دسترسی به اطلاعات ساختاریافته استفاده کنید.\n"
            "- برای سوالات خاص، پیام خود را تایپ کنید تا با هوش مصنوعی پاسخ داده شود.\n"
            "- از دکمه 'تماس با ادمین' برای ارسال پیام مستقیم به مدیر ربات استفاده کنید."
        )
        await query.edit_message_text(help_text, reply_markup=keyboard)

    return MAIN_MENU
