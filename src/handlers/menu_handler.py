import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from src.config import logger
from src.utils.keyboard_builder import get_main_menu_keyboard
from src.utils.text_formatter import sanitize_markdown

async def main_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نمایش منوی اصلی."""
    from src.handlers.user_manager import MAIN_MENU
    lang = context.user_data.get('language', 'fa')
    messages = {
        'fa': "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        'en': "Please select one of the following options:",
        'it': "Seleziona una delle seguenti opzioni:"
    }
    try:
        await update.message.reply_text(
            sanitize_markdown(messages.get(lang, messages['fa'])),
            parse_mode='MarkdownV2',
            reply_markup=get_main_menu_keyboard(lang)
        )
    except Exception as e:
        logger.error(f"Error displaying main menu: {e}")
        await update.message.reply_text(
            sanitize_markdown("خطایی رخ داد. لطفاً دوباره امتحان کنید." if lang == 'fa' else
                            "An error occurred. Please try again." if lang == 'en' else
                            "Si è verificato un errore. Riprova."),
            parse_mode='MarkdownV2'
        )
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نمایش راهنما."""
    from src.handlers.user_manager import MAIN_MENU
    lang = context.user_data.get('language', 'fa')
    messages = {
        'fa': (
            "📚 *راهنما*\n"
            "این ربات برای کمک به دانشجویان دانشگاه پروجا طراحی شده است.\n"
            "- *محاسبه ISEE*: برای محاسبه شاخص ISEE.\n"
            "- *جستجو*: جستجو در اطلاعات بورسیه‌ها و تقویم.\n"
            "- *تماس با ادمین*: برای ارتباط با ادمین.\n"
            "- *تغییر زبان*: برای تغییر زبان ربات.\n"
            "برای شروع، از منوی زیر استفاده کنید."
        ),
        'en': (
            "📚 *Help*\n"
            "This bot is designed to assist students at the University of Perugia.\n"
            "- *Calculate ISEE*: To calculate the ISEE index.\n"
            "- *Search*: Search through scholarships and calendar info.\n"
            "- *Contact Admin*: To contact the admin.\n"
            "- *Change Language*: To change the bot's language.\n"
            "Use the menu below to get started."
        ),
        'it': (
            "📚 *Aiuto*\n"
            "Questo bot è progettato per aiutare gli studenti dell'Università di Perugia.\n"
            "- *Calcola ISEE*: Per calcolare l'indice ISEE.\n"
            "- *Cerca*: Cerca informazioni su borse di studio e calendario.\n"
            "- *Contatta Admin*: Per contattare l'amministratore.\n"
            "- *Cambia Lingua*: Per cambiare la lingua del bot.\n"
            "Usa il menu qui sotto per iniziare."
        )
    }
    try:
        await update.message.reply_text(
            sanitize_markdown(messages.get(lang, messages['fa'])),
            parse_mode='MarkdownV2',
            reply_markup=get_main_menu_keyboard(lang)
        )
    except Exception as e:
        logger.error(f"Error displaying help: {e}")
        await update.message.reply_text(
            sanitize_markdown("خطایی رخ داد. لطفاً دوباره امتحان کنید." if lang == 'fa' else
                            "An error occurred. Please try again." if lang == 'en' else
                            "Si è verificato un errore. Riprova."),
            parse_mode='MarkdownV2'
        )
    return MAIN_MENU

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت انتخاب منو."""
    from src.handlers.user_manager import SELECTING_LANG, MAIN_MENU
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('language', 'fa')

    if query.data == "menu:main_menu":
        return await main_menu_command(update, context)
    elif query.data == "menu:change_language":
        messages = {
            'fa': "لطفاً زبان موردنظر خود را انتخاب کنید:",
            'en': "Please select your preferred language:",
            'it': "Seleziona la lingua preferita:"
        }
        buttons = [
            [InlineKeyboardButton("فارسی 🇮🇷", callback_data="lang:fa"),
             InlineKeyboardButton("English 🇬🇧", callback_data="lang:en"),
             InlineKeyboardButton("Italiano 🇮🇹", callback_data="lang:it")]
        ]
        try:
            await query.message.edit_text(
                sanitize_markdown(messages.get(lang, messages['fa'])),
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            logger.error(f"Error handling menu callback: {e}")
            await query.message.edit_text(
                sanitize_markdown("خطایی رخ داد. لطفاً دوباره امتحان کنید." if lang == 'fa' else
                                "An error occurred. Please try again." if lang == 'en' else
                                "Si è verificato un errore. Riprova."),
                parse_mode='MarkdownV2'
            )
        return SELECTING_LANG
    return MAIN_MENU

async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت اقدامات انتخاب‌شده توسط کاربر."""
    from src.handlers.user_manager import MAIN_MENU
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('language', 'fa')

    action = query.data.replace("action:", "")
    if action == "isee":
        from src.services.isee_service import start_isee_calculation
        return await start_isee_calculation(update, context)
    elif action == "search":
        messages = {
            'fa': "لطفاً عبارت موردنظر برای جستجو را وارد کنید:",
            'en': "Please enter the search query:",
            'it': "Inserisci la query di ricerca:"
        }
        context.user_data['awaiting_search_query'] = True
        try:
            await query.message.edit_text(
                sanitize_markdown(messages.get(lang, messages['fa'])),
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🔙 بازگشت" if lang == 'fa' else "🔙 Back" if lang == 'en' else "🔙 Indietro",
                        callback_data="menu:main_menu"
                    )
                ]])
            )
        except Exception as e:
            logger.error(f"Error prompting for search query: {e}")
            await query.message.edit_text(
                sanitize_markdown("خطایی رخ داد. لطفاً دوباره امتحان کنید." if lang == 'fa' else
                                "An error occurred. Please try again." if lang == 'en' else
                                "Si è verificato un errore. Riprova."),
                parse_mode='MarkdownV2'
            )
        return MAIN_MENU
    elif action == "contact_admin":
        messages = {
            'fa': "لطفاً پیام خود را برای ادمین بنویسید:",
            'en': "Please write your message for the admin:",
            'it': "Scrivi il tuo messaggio per l'admin:"
        }
        context.user_data['next_message_is_admin_contact'] = True
        try:
            await query.message.edit_text(
                sanitize_markdown(messages.get(lang, messages['fa'])),
                parse_mode='MarkdownV2',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🔙 بازگشت" if lang == 'fa' else "🔙 Back" if lang == 'en' else "🔙 Indietro",
                        callback_data="menu:main_menu"
                    )
                ]])
            )
        except Exception as e:
            logger.error(f"Error prompting for admin contact: {e}")
            await query.message.edit_text(
                sanitize_markdown("خطایی رخ داد. لطفاً دوباره امتحان کنید." if lang == 'fa' else
                                "An error occurred. Please try again." if lang == 'en' else
                                "Si è verificato un errore. Riprova."),
                parse_mode='MarkdownV2'
            )
        return MAIN_MENU
    return MAIN_MENU
