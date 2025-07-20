import logging
from telegram import Update
from telegram.ext import ContextTypes
import os

from src.utils.keyboard_builder import get_main_menu_keyboard, get_item_keyboard, get_content_keyboard
from src.data.knowledge_base import get_content_by_path
from src.utils.text_formatter import sanitize_markdown
from src.config import logger, ADMIN_CHAT_ID
from src.locale import get_message
from src.handlers.user_manager import MAIN_MENU
from src.handlers import isee_handler, search_handler

async def main_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /menu command."""
    lang = context.user_data.get('language', 'fa')
    await update.message.reply_text(
        text=get_message("main_menu_prompt", lang),
        reply_markup=get_main_menu_keyboard(lang)
    )
    return MAIN_MENU

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles all menu navigation callbacks."""
    query = update.callback_query
    await query.answer()

    path = query.data.split(":")[1:]
    lang = context.user_data.get('language', 'fa')

    if not path or path[0] == "main_menu":
        context.user_data['current_path'] = []
        await query.edit_message_text(
            text=get_message("main_menu_prompt", lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
        return MAIN_MENU

    context.user_data['current_path'] = path

    if len(path) == 1: # Category selected
        category = path[0]
        await query.edit_message_text(
            text=get_message("category_selected", lang, category=category),
            reply_markup=get_item_keyboard(category, lang)
        )

    elif len(path) == 2: # Item selected
        content, file_path = get_content_by_path(path, lang)
        sanitized_content = sanitize_markdown(content)

        await query.edit_message_text(
            text=sanitized_content,
            parse_mode='MarkdownV2',
            reply_markup=get_content_keyboard(path, lang)
        )

        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as file:
                    if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                        await context.bot.send_photo(chat_id=query.from_user.id, photo=file)
                    else:
                        await context.bot.send_document(chat_id=query.from_user.id, document=file)
            except Exception as e:
                logger.error(f"Error sending file {file_path}: {e}")
                await context.bot.send_message(chat_id=query.from_user.id, text=get_message("file_send_error", lang))
        elif file_path:
            logger.warning(f"File not found at path: {file_path}")
            await context.bot.send_message(chat_id=query.from_user.id, text=get_message("file_not_found", lang))

    return MAIN_MENU

async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles callbacks for static action buttons."""
    query = update.callback_query
    action = query.data.split(":")[1]
    lang = context.user_data.get('language', 'fa')

    if action == "start_isee":
        await query.answer()
        await query.edit_message_text(get_message("start_isee", lang))
        return isee_handler.INCOME

    elif action == "start_search":
        await query.answer()
        await query.edit_message_text(get_message("ask_search_query", lang))
        return search_handler.ASKING_QUERY

    elif action == "help":
        await query.answer()
        await query.edit_message_text(
            get_message("help_text", lang),
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard(lang)
        )

    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /help command."""
    lang = context.user_data.get('language', 'fa')
    await update.message.reply_text(
        get_message("help_text", lang),
        parse_mode='Markdown',
        reply_markup=get_main_menu_keyboard(lang)
    )
    return MAIN_MENU
