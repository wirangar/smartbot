import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.config import logger
from src.utils.keyboard_builder import get_main_menu_keyboard
from src.utils.text_formatter import sanitize_markdown
from src.data.knowledge_base import get_scholarships, get_academic_calendar
from src.services.google_sheets_service import get_scholarships_from_sheet, get_user_history_from_sheet
import aiohttp

async def main_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
 """نمایش منوی اصلی."""
 from src.handlers.user_manager import MAIN_MENU
 if 'language' not in context.user_data:
 context.user_data['language'] = 'fa'
 lang = context.user_data['language']
 await update.message.reply_text(
 sanitize_markdown("لطفاً یک گزینه انتخاب کنید:" if lang == 'fa' else
 "Please select an option:" if lang == 'en' else
 "Seleziona un'opzione:"),
 reply_markup=get_main_menu_keyboard(lang),
 parse_mode='MarkdownV2'
 )
 return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
 """نمایش پیام راهنما."""
 from src.handlers.user_manager import MAIN_MENU
 lang = context.user_data.get('language', 'fa')
 help_text = {
 'fa': (
 "📖 *راهنمای ربات*\n\n"
 "این ربات برای کمک به دانشجویان در پروجا طراحی شده است:\n"
 "- *بورسیه‌ها*: اطلاعات بورسیه‌های تحصیلی.\n"
 "- *تقویم تحصیلی*: برنامه دانشگاه.\n"
 "- *آب‌وهوا*: وضعیت آب‌وهوای پروجا.\n"
 "- *جستجو*: جستجوی اطلاعات.\n"
 "- *تماس با ادمین*: ارسال پیام به ادمین.\n"
 "- *محاسبه ISEE*: محاسبه شاخص ISEE برای بورسیه.\n"
 "- *پروفایل*: مشاهده اطلاعات ثبت‌شده.\n"
 "برای لغو هر عملیات از /cancel استفاده کنید."
 ),
 'en': (
 "📖 *Bot Help*\n\n"
 "This bot is designed to assist students in Perugia:\n"
 "- *Scholarships*: Information about academic scholarships.\n"
 "- *Academic Calendar*: University schedule.\n"
 "- *Weather*: Perugia weather status.\n"
 "- *Search*: Search for information.\n"
 "- *Contact Admin*: Send a message to the admin.\n"
 "- *Calculate ISEE*: Calculate ISEE index for scholarships.\n"
 "- *Profile*: View registered information.\n"
 "Use /cancel to stop any operation."
 ),
 'it': (
 "📖 *Aiuto Bot*\n\n"
 "Questo bot è progettato per aiutare gli studenti a Perugia:\n"
 "- *Borse di studio*: Informazioni sulle borse di studio.\n"
 "- *Calendario accademico*: Programma universitario.\n"
 "- *Meteo*: Stato del tempo a Perugia.\n"
 "- *Cerca*: Cerca informazioni.\n"
 "- *Contatta l'admin*: Invia un messaggio all'admin.\n"
 "- *Calcola ISEE*: Calcola l'indice ISEE per le borse.\n"
 "- *Profilo*: Visualizza le informazioni registrate.\n"
 "Usa /cancel per interrompere qualsiasi operazione."
 )
 }
 await update.message.reply_text(
 sanitize_markdown(help_text.get(lang)),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 return MAIN_MENU

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
 """مدیریت انتخاب‌های منوی اصلی."""
 from src.handlers.user_manager import MAIN_MENU
 query = update.callback_query
 await query.answer()
 lang = context.user_data.get('language', 'fa')

 menu_selection = query.data.replace("menu:", "")
 logger.info(f"User {query.from_user.id} selected menu: {menu_selection}")

 if menu_selection in ["بورسیه‌ها", "Scholarships", "Borse di studio"]:
 scholarships = await get_scholarships_from_sheet(lang)
 if scholarships:
 keyboard = [
 [InlineKeyboardButton(s['title'], callback_data=f"action:scholarship_{i}")]
 for i, s in enumerate(scholarships)
 ]
 back_text = {"fa": "🔙 بازگشت", "en": "🔙 Back", "it": "🔙 Indietro"}
 keyboard.append([InlineKeyboardButton(back_text.get(lang), callback_data="menu:main_menu")])
 await query.message.reply_text(
 sanitize_markdown("📚 بورسیه‌ها:" if lang == 'fa' else
 "📚 Scholarships:" if lang == 'en' else
 "📚 Borse di studio:"),
 reply_markup=InlineKeyboardMarkup(keyboard),
 parse_mode='MarkdownV2'
 )
 else:
 await query.message.reply_text(
 sanitize_markdown("هیچ بورسیه‌ای یافت نشد." if lang == 'fa' else
 "No scholarships found." if lang == 'en' else
 "Nessuna borsa di studio trovata."),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 elif menu_selection in ["تقویم تحصیلی", "Academic Calendar", "Calendario accademico"]:
 calendar = get_academic_calendar(lang)
 if calendar:
 keyboard = [
 [InlineKeyboardButton(item['title'], callback_data=f"action:calendar_{i}")]
 for i, item in enumerate(calendar)
 ]
 back_text = {"fa": "🔙 بازگشت", "en": "🔙 Back", "it": "🔙 Indietro"}
 keyboard.append([InlineKeyboardButton(back_text.get(lang), callback_data="menu:main_menu")])
 await query.message.reply_text(
 sanitize_markdown("📅 تقویم تحصیلی:" if lang == 'fa' else
 "📅 Academic Calendar:" if lang == 'en' else
 "📅 Calendario accademico:"),
 reply_markup=InlineKeyboardMarkup(keyboard),
 parse_mode='MarkdownV2'
 )
 else:
 await query.message.reply_text(
 sanitize_markdown("هیچ تقویمی یافت نشد." if lang == 'fa' else
 "No academic calendar found." if lang == 'en' else
 "Nessun calendario accademico trovato."),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 elif menu_selection in ["آب‌وهوا", "Weather", "Meteo"]:
 async with aiohttp.ClientSession() as session:
 async with session.get(
 f"http://api.openweathermap.org/data/2.5/weather?q=Perugia,IT&appid={context.bot_data['OPENWEATHERMAP_API_KEY']}&units=metric"
 ) as response:
 if response.status == 200:
 data = await response.json()
 weather = data['weather'][0]['description']
 temp = data['main']['temp']
 humidity = data['main']['humidity']
 weather_text = {
 'fa': f"🌦️ وضعیت آب‌وهوا در پروجا:\n- شرایط: {weather}\n- دما: {temp}°C\n- رطوبت: {humidity}%",
 'en': f"🌦️ Weather in Perugia:\n- Condition: {weather}\n- Temperature: {temp}°C\n- Humidity: {humidity}%",
 'it': f"🌦️ Meteo a Perugia:\n- Condizione: {weather}\n- Temperatura: {temp}°C\n- Umidità: {humidity}%"
 }
 await query.message.reply_text(
 sanitize_markdown(weather_text.get(lang)),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 else:
 await query.message.reply_text(
 sanitize_markdown("خطا در دریافت وضعیت آب‌وهوا." if lang == 'fa' else
 "Error fetching weather data." if lang == 'en' else
 "Errore nel recupero dei dati meteo."),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 elif menu_selection in ["جستجو", "Search", "Cerca"]:
 context.user_data['awaiting_search_query'] = True
 await query.message.reply_text(
 sanitize_markdown("لطفاً عبارت جستجو را وارد کنید:" if lang == 'fa' else
 "Please enter your search query:" if lang == 'en' else
 "Inserisci la query di ricerca:"),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 elif menu_selection in ["تماس با ادمین", "Contact Admin", "Contatta l'admin"]:
 context.user_data['next_message_is_admin_contact'] = True
 await query.message.reply_text(
 sanitize_markdown("لطفاً پیام خود را برای ادمین بنویسید:" if lang == 'fa' else
 "Please write your message to the admin:" if lang == 'en' else
 "Scrivi il tuo messaggio per l'admin:"),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 elif menu_selection in ["محاسبه ISEE", "Calculate ISEE", "Calcola ISEE"]:
 from src.services.isee_service import ISEEService
 isee_service = ISEEService(context.bot_data.get('knowledge_base', {}), context.bot_data.get('db_manager'))
 return await isee_service.start(update, context)
 else:
 await query.message.reply_text(
 sanitize_markdown("گزینه نامعتبر!" if lang == 'fa' else
 "Invalid option!" if lang == 'en' else
 "Opzione non valida!"),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 return MAIN_MENU

async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
 """مدیریت انتخاب‌های مربوط به آیتم‌ها."""
 from src.handlers.user_manager import MAIN_MENU
 query = update.callback_query
 await query.answer()
 lang = context.user_data.get('language', 'fa')

 action = query.data.replace("action:", "")
 if action.startswith("scholarship_"):
 idx = int(action.replace("scholarship_", ""))
 scholarships = await get_scholarships_from_sheet(lang)
 if idx < len(scholarships):
 scholarship = scholarships[idx]
 text = (
 f"*{scholarship['title']}*\n\n"
 f"{scholarship['description']}\n\n"
 f"📅 *مهلت*: {scholarship['deadline']}\n"
 f"🔗 *لینک*: {scholarship['link']}"
 )
 await query.message.reply_text(
 sanitize_markdown(text),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 else:
 await query.message.reply_text(
 sanitize_markdown("بورسیه یافت نشد." if lang == 'fa' else
 "Scholarship not found." if lang == 'en' else
 "Borsa di studio non trovata."),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 elif action.startswith("calendar_"):
 idx = int(action.replace("calendar_", ""))
 calendar = get_academic_calendar(lang)
 if idx < len(calendar):
 item = calendar[idx]
 text = f"*{item['title']}*\n\n{item['content']}"
 await query.message.reply_text(
 sanitize_markdown(text),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 else:
 await query.message.reply_text(
 sanitize_markdown("مورد تقویمی یافت نشد." if lang == 'fa' else
 "Calendar item not found." if lang == 'en' else
 "Elemento del calendario non trovato."),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 else:
 await query.message.reply_text(
 sanitize_markdown("گزینه نامعتبر!" if lang == 'fa' else
 "Invalid option!" if lang == 'en' else
 "Opzione non valida!"),
 parse_mode='MarkdownV2',
 reply_markup=get_main_menu_keyboard(lang)
 )
 return MAIN_MENU
