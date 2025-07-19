import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from src.config import logger
from src.locale import get_message
from src.services.search_service import SearchService
from src.services.paginator_service import PaginatorService

# Conversation states
ASKING_QUERY, SHOWING_RESULTS = range(2)

# Initialize services
search_service = SearchService()
paginator_service = PaginatorService()

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the search conversation."""
    lang = context.user_data.get('language', 'fa')

    # This can be triggered by a command or a callback query
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=get_message("ask_search_query", lang))
    else:
        await update.message.reply_text(get_message("ask_search_query", lang))

    return ASKING_QUERY

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's search query and displays results."""
    user_message = update.message.text
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'fa')

    search_results = search_service.search(user_message, lang)

    if not search_results:
        await update.message.reply_text(get_message("no_search_results", lang, query=user_message))
        return ConversationHandler.END

    paginator_service.create_session(user_id, search_results)
    first_page = paginator_service.get_current_page(user_id)

    message_text = f"🔎 {get_message('search_results', lang, query=user_message)}\n\n"
    message_text += f"*{first_page['content']['title']}*\n{first_page['content']['snippet']}"

    keyboard = [[
        InlineKeyboardButton(get_message('view_button', lang), callback_data=first_page['content']['callback']),
        InlineKeyboardButton(f"1/{first_page['total_pages']}", callback_data="noop"),
    ]]
    if first_page['total_pages'] > 1:
        keyboard[0].append(InlineKeyboardButton(get_message('next_button', lang), callback_data="pagination:next"))

    await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    return SHOWING_RESULTS

async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the search conversation."""
    lang = context.user_data.get('language', 'fa')
    await update.message.reply_text(get_message("search_cancelled", lang))
    return ConversationHandler.END
