import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.config import ADMIN_CHAT_ID, logger
from src.services.openai_service import get_ai_response, process_voice_message
from src.services.google_sheets_service import append_qa_to_sheet
from src.services.search_service import SearchService
from src.services.paginator_service import PaginatorService
from src.utils.keyboard_builder import get_main_menu_keyboard
from src.locale import get_message
from src.handlers.user_manager import MAIN_MENU

# Initialize services
search_service = SearchService()
paginator_service = PaginatorService()

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles incoming text messages, performing search or falling back to AI."""
    user_message = update.message.text
    user = update.effective_user
    lang = context.user_data.get('language', 'fa')

    # Admin contact logic
    if context.user_data.get('next_message_is_admin_contact'):
        context.user_data['next_message_is_admin_contact'] = False
        if ADMIN_CHAT_ID:
            try:
                user_info = f"Message from: {user.full_name} (ID: {user.id})"
                await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=user_info)
                await context.bot.forward_message(chat_id=ADMIN_CHAT_ID, from_chat_id=user.id, message_id=update.message.message_id)
                await update.message.reply_text(get_message("contact_success", lang))
            except Exception as e:
                logger.error(f"Failed to forward message to admin: {e}")
                await update.message.reply_text(get_message("contact_error", lang))
        return MAIN_MENU

    # Search in knowledge base first
    search_results = search_service.search(user_message, lang)

    if search_results:
        paginator_service.create_session(user.id, search_results)
        first_page = paginator_service.get_current_page(user.id)

        message_text = f"🔎 {get_message('search_results', lang, query=user_message)}\n\n"
        message_text += f"*{first_page['content']['title']}*\n{first_page['content']['snippet']}"

        keyboard = [[
            InlineKeyboardButton(get_message('view_button', lang), callback_data=first_page['content']['callback']),
            InlineKeyboardButton(f"1/{first_page['total_pages']}", callback_data="noop"),
            InlineKeyboardButton(get_message('next_button', lang), callback_data="pagination:next"),
        ]]

        await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MAIN_MENU

    # Fallback to OpenAI if no search results
    ai_response = await get_ai_response(user_message, lang)
    if ai_response:
        await append_qa_to_sheet(user.id, user_message, ai_response)

        # Ask for feedback
        feedback_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(get_message("feedback_yes", lang), callback_data=f"feedback:yes:{update.message.message_id}"),
                InlineKeyboardButton(get_message("feedback_no", lang), callback_data=f"feedback:no:{update.message.message_id}")
            ]
        ])
        await update.message.reply_text(ai_response, reply_markup=feedback_keyboard)

    else:
        ai_response = get_message("ai_error", lang)
        await update.message.reply_text(ai_response, reply_markup=get_main_menu_keyboard(lang))

    return MAIN_MENU

async def handle_pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles next/prev page buttons for search results."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get('language', 'fa')
    action = query.data.split(":")[1]

    if action == "next":
        page_data = paginator_service.get_next_page(user_id)
    else: # prev
        page_data = paginator_service.get_prev_page(user_id)

    if page_data:
        message_text = f"*{page_data['content']['title']}*\n{page_data['content']['snippet']}"

        # Build dynamic keyboard
        buttons = []
        if page_data['page_num'] > 1:
            buttons.append(InlineKeyboardButton(get_message('prev_button', lang), callback_data="pagination:prev"))

        buttons.append(InlineKeyboardButton(f"{page_data['page_num']}/{page_data['total_pages']}", callback_data="noop"))
        buttons.append(InlineKeyboardButton(get_message('view_button', lang), callback_data=page_data['content']['callback']))

        if page_data['page_num'] < page_data['total_pages']:
            buttons.append(InlineKeyboardButton(get_message('next_button', lang), callback_data="pagination:next"))

        await query.edit_message_text(message_text, reply_markup=InlineKeyboardMarkup([buttons]), parse_mode='Markdown')

    return MAIN_MENU

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles incoming voice messages."""
    user = update.effective_user
    lang = context.user_data.get('language', 'fa')

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        temp_dir = Path("./temp_audio")
        temp_dir.mkdir(exist_ok=True)
        temp_voice_path = temp_dir / f"{update.message.voice.file_id}.ogg"

        await voice_file.download_to_drive(temp_voice_path)
        transcribed_text = await process_voice_message(temp_voice_path, lang)

        if transcribed_text:
            await update.message.reply_text(f"{get_message('voice_transcribed', lang)}: *{transcribed_text}*\n{get_message('processing', lang)}...", parse_mode='Markdown')
            update.message.text = transcribed_text
            return await handle_text_message(update, context)
        else:
            await update.message.reply_text(get_message("voice_error", lang))

    except Exception as e:
        logger.error(f"Error handling voice message for user {user.id}: {e}")
        await update.message.reply_text(get_message("voice_error_generic", lang))

    return MAIN_MENU

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles file uploads and forwards them to the admin."""
    user = update.effective_user
    lang = context.user_data.get('language', 'fa')

    if ADMIN_CHAT_ID:
        try:
            user_info = f"File uploaded by: {user.full_name} (ID: {user.id})"
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=user_info)
            await context.bot.forward_message(chat_id=ADMIN_CHAT_ID, from_chat_id=user.id, message_id=update.message.message_id)
            await update.message.reply_text(get_message("file_upload_success", lang))
        except Exception as e:
            logger.error(f"Failed to forward file to admin: {e}")
            await update.message.reply_text(get_message("file_upload_error", lang))
    else:
        await update.message.reply_text(get_message("feature_unavailable", lang))
