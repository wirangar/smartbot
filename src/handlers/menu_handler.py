import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from src.config import logger
from src.utils.keyboard_builder import get_main_menu_keyboard, get_item_keyboard
from src.utils.text_formatter import sanitize_markdown
from src.services.openai_service import get_ai_response
from src.services.google_sheets_service import append_qa_to_sheet
from src.data.knowledge_base import get_knowledge_base, get_content_by_path

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
            "- *بورسیه‌ها*: اطلاعات بورسیه‌های موجود.\n"
            "- *تقویم تحصیلی*: تقویم دانشگاه پروجا.\n"
            "- *آب‌وهوا*: وضعیت آب‌وهوای پروجا.\n"
            "- *جستجو*: جستجو در اطلاعات بورسیه‌ها و تقویم.\n"
            "- *محاسبه ISEE*: برای محاسبه شاخص ISEE.\n"
            "- *تماس با ادمین*: برای ارتباط با ادمین.\n"
            "- *پروفایل*: مشاهده اطلاعات پروفایل.\n"
            "- *تغییر زبان*: تغییر زبان ربات.\n"
            "برای شروع، از منوی زیر استفاده کنید."
        ),
        'en': (
            "📚 *Help*\n"
            "This bot is designed to assist students at the University of Perugia.\n"
            "- *Scholarships*: Information on available scholarships.\n"
            "- *Academic Calendar*: University of Perugia calendar.\n"
            "- *Weather*: Weather status in Perugia.\n"
            "- *Search*: Search through scholarships and calendar info.\n"
            "- *Calculate ISEE*: To calculate the ISEE index.\n"
            "- *Contact Admin*: To contact the admin.\n"
            "- *Profile*: View profile information.\n"
            "- *Change Language*: Change the bot's language.\n"
            "Use the menu below to get started."
        ),
        'it': (
            "📚 *Aiuto*\n"
            "Questo bot è progettato per aiutare gli studenti dell'Università di Perugia.\n"
            "- *Borse di studio*: Informazioni sulle borse di studio disponibili.\n"
            "- *Calendario accademico*: Calendario dell'Università di Perugia.\n"
            "- *Meteo*: Stato del tempo a Perugia.\n"
            "- *Cerca*: Cerca informazioni su borse di studio e calendario.\n"
            "- *Calcola ISEE*: Per calcolare l'indice ISEE.\n"
            "- *Contatta Admin*: Per contattare l'amministratore.\n"
            "- *Profilo*: Visualizza le informazioni del profilo.\n"
            "- *Cambia Lingua*: Cambia la lingua del bot.\n"
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
    elif query.data == "menu:scholarships":
        kb = get_knowledge_base()
        scholarships = kb.get('بورسیه و تقویم آموزشی', [])
        if not scholarships:
            messages = {
                'fa': "❌ اطلاعاتی درباره بورسیه‌ها یافت نشد.",
                'en': "❌ No scholarship information found.",
                'it': "❌ Nessuna informazione sulle borse di studio trovata."
            }
            await query.message.edit_text(
                sanitize_markdown(messages.get(lang, messages['fa'])),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
            return MAIN_MENU
        items = [{'title': item.get('title', {}).get(lang, item.get('title', {}).get('en', '')), 'callback': f"menu:بورسیه و تقویم آموزشی:{item.get('id', '')}"} for item in scholarships]
        await query.message.edit_text(
            sanitize_markdown("لطفاً یک بورسیه را انتخاب کنید:" if lang == 'fa' else
                            "Please select a scholarship:" if lang == 'en' else
                            "Seleziona una borsa di studio:"),
            parse_mode='MarkdownV2',
            reply_markup=get_item_keyboard(items, lang)
        )
        return MAIN_MENU
    elif query.data == "menu:calendar":
        kb = get_knowledge_base()
        calendar = kb.get('تقویم تحصیلی', [])
        if not calendar:
            messages = {
                'fa': "❌ اطلاعاتی درباره تقویم تحصیلی یافت نشد.",
                'en': "❌ No academic calendar information found.",
                'it': "❌ Nessuna informazione sul calendario accademico trovata."
            }
            await query.message.edit_text(
                sanitize_markdown(messages.get(lang, messages['fa'])),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
            return MAIN_MENU
        items = [{'title': item.get('title', {}).get(lang, item.get('title', {}).get('en', '')), 'callback': f"menu:تقویم تحصیلی:{item.get('id', '')}"} for item in calendar]
        await query.message.edit_text(
            sanitize_markdown("لطفاً یک تقویم را انتخاب کنید:" if lang == 'fa' else
                            "Please select a calendar:" if lang == 'en' else
                            "Seleziona un calendario:"),
            parse_mode='MarkdownV2',
            reply_markup=get_item_keyboard(items, lang)
        )
        return MAIN_MENU
    elif query.data == "menu:weather":
        messages = {
            'fa': "در حال دریافت وضعیت آب‌وهوا...",
            'en': "Fetching weather information...",
            'it': "Recupero delle informazioni meteo..."
        }
        await query.message.edit_text(
            sanitize_markdown(messages.get(lang, messages['fa'])),
            parse_mode='MarkdownV2'
        )
        try:
            weather_response = await get_ai_response("Current weather in Perugia, Italy", lang)
            await query.message.edit_text(
                sanitize_markdown(weather_response),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
        except Exception as e:
            logger.error(f"Error fetching weather for user {query.from_user.id}: {e}")
            messages = {
                'fa': "❌ خطایی در دریافت آب‌وهوا رخ داد.",
                'en': "❌ An error occurred while fetching weather.",
                'it': "❌ Si è verificato un errore durante il recupero del meteo."
            }
            await query.message.edit_text(
                sanitize_markdown(messages.get(lang, messages['fa'])),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
        return MAIN_MENU
    elif query.data == "menu:profile":
        from src.handlers.user_manager import show_profile_command
        return await show_profile_command(update, context)
    elif query.data == "menu:help":
        return await help_command(update, context)
    elif query.data.startswith("menu:بورسیه و تقویم آموزشی:") or query.data.startswith("menu:تقویم تحصیلی:"):
        path_parts = query.data.replace("menu:", "").split(":")
        content, file_path = get_content_by_path(path_parts, lang)
        await query.message.edit_text(
            sanitize_markdown(content),
            parse_mode='MarkdownV2',
            reply_markup=get_main_menu_keyboard(lang)
        )
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    if file_path.endswith(('.jpg', '.jpeg', '.png')):
                        await query.message.reply_photo(photo=f)
                    elif file_path.endswith('.pdf'):
                        await query.message.reply_document(document=f)
            except Exception as e:
                logger.error(f"Error sending file {file_path} for user {query.from_user.id}: {e}")
        return MAIN_MENU
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
