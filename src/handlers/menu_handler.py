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

# A simple in-memory cache for user history. In a real-world scenario, this might be moved to Redis.
user_history = {}

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main menu."""
    lang = context.user_data.get('language', 'fa')
    menu_text = {
        'fa': "لطفاً یک گزینه را از منوی اصلی انتخاب کنید:",
        'en': "Please select an option from the main menu:",
        'it': "Seleziona un'opzione dal menu principale:"
    }

    # Check if we are editing a message (from a callback query) or sending a new one
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=menu_text.get(lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
    else:
        await update.message.reply_text(
            text=menu_text.get(lang),
            reply_markup=get_main_menu_keyboard(lang)
        )

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles all menu navigation callbacks."""
    query = update.callback_query
    await query.answer()

    path = query.data.split(":")[1:]
    lang = context.user_data.get('language', 'fa')

    if not path or path[0] == "main_menu":
        context.user_data['current_path'] = []
        await main_menu(update, context)
        return MAIN_MENU

    context.user_data['current_path'] = path

    if len(path) == 1: # Category selected
        category = path[0]
        category_text = {'fa': f"شما دسته بندی '{category}' را انتخاب کردید. لطفاً یک مورد را انتخاب کنید:", 'en': f"You selected '{category}'. Please choose an item:", 'it': f"Hai selezionato '{category}'. Scegli un elemento:"}
        await query.edit_message_text(
            text=category_text.get(lang),
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
                    else: # Assuming PDF or other documents
                        await context.bot.send_document(chat_id=query.from_user.id, document=file)
            except Exception as e:
                logger.error(f"Error sending file {file_path} for user {query.from_user.id}: {e}")
                error_text = {'fa': "خطایی در ارسال فایل رخ داد.", 'en': "An error occurred while sending the file.", 'it': "Si è verificato un errore durante l'invio del file."}
                await context.bot.send_message(chat_id=query.from_user.id, text=error_text.get(lang))
        elif file_path:
            logger.warning(f"File not found at path: {file_path}")
            not_found_text = {'fa': "فایل مرتبط یافت نشد.", 'en': "Associated file not found.", 'it': "File associato non trovato."}
            await context.bot.send_message(chat_id=query.from_user.id, text=not_found_text.get(lang))

    return MAIN_MENU

async def main_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /menu command."""
    await main_menu(update, context)
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /help command."""
    lang = context.user_data.get('language', 'fa')
    help_text_map = {
        'fa': "🤖 *راهنمای ربات Scholarino*\n\n- از منوها برای دسترسی به اطلاعات استفاده کنید.\n- برای سوالات خاص، پیام خود را تایپ کنید.\n- برای تماس با مدیر، از دکمه 'تماس با ادمین' استفاده کنید.",
        'en': "🤖 *Scholarino Bot Help*\n\n- Use the menus to access information.\n- For specific questions, type your message.\n- Use the 'Contact Admin' button to reach the administrator.",
        'it': "🤖 *Aiuto Bot Scholarino*\n\n- Usa i menu per accedere alle informazioni.\n- Per domande specifiche, digita il tuo messaggio.\n- Usa il pulsante 'Contatta Admin' per raggiungere l'amministratore."
    }
    await update.message.reply_text(help_text_map.get(lang), parse_mode='Markdown', reply_markup=get_main_menu_keyboard(lang))
    return MAIN_MENU

async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles callbacks for static action buttons like help, profile, etc."""
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1]
    lang = context.user_data.get('language', 'fa')

    if action == "profile":
        # This will be handled by the user_manager.py's show_profile function
        # We can add a direct call here if needed, but for now, let's keep it in the main handler registration
        pass

    elif action == "contact_admin":
        context.user_data['next_message_is_admin_contact'] = True
        contact_text = {
            'fa': "لطفاً پیام خود را برای ارسال به ادمین تایپ کنید. پیام شما مستقیماً به ادمین ارسال خواهد شد.",
            'en': "Please type your message to the admin. It will be forwarded directly.",
            'it': "Scrivi il tuo messaggio per l'admin. Sarà inoltrato direttamente."
        }
        await query.edit_message_text(text=contact_text.get(lang))

    elif action == "calculate_isee":
        # Transition to the ISEE conversation
        from . import isee_handler
        await query.message.reply_text(get_message("start_isee", lang))
        return isee_handler.INCOME

    elif action == "history":
        # Placeholder for history functionality
        history_text_map = {
            'fa': "📜 تاریخچه پرسش و پاسخ شما در اینجا نمایش داده خواهد شد.",
            'en': "📜 Your Q&A history will be displayed here.",
            'it': "📜 La tua cronologia di domande e risposte sarà visualizzata qui."
        }
        await query.edit_message_text(history_text_map.get(lang), reply_markup=get_main_menu_keyboard(lang))

    elif action == "help":
        help_text_map = {
            'fa': "🤖 *راهنمای ربات Scholarino*\n\n- از منوها برای دسترسی به اطلاعات استفاده کنید.\n- برای سوالات خاص، پیام خود را تایپ کنید.\n- برای تماس با مدیر، از دکمه 'تماس با ادمین' استفاده کنید.",
            'en': "🤖 *Scholarino Bot Help*\n\n- Use the menus to access information.\n- For specific questions, type your message.\n- Use the 'Contact Admin' button to reach the administrator.",
            'it': "🤖 *Aiuto Bot Scholarino*\n\n- Usa i menu per accedere alle informazioni.\n- Per domande specifiche, digita il tuo messaggio.\n- Usa il pulsante 'Contatta Admin' per raggiungere l'amministratore."
        }
        await query.edit_message_text(help_text_map.get(lang), parse_mode='Markdown', reply_markup=get_main_menu_keyboard(lang))

    return MAIN_MENU
