import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from src.config import logger
from src.utils.keyboard_builder import get_main_menu_keyboard, get_item_keyboard
from src.utils.text_formatter import sanitize_markdown
from src.services.openai_service import get_ai_response
from src.services.google_sheets_service import append_qa_to_sheet

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
            'fa': "لطف
