from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.config import logger
from src.utils.text_formatter import escape_markdown_v2

def get_main_menu_keyboard(lang: str = 'fa') -> InlineKeyboardMarkup:
 """ایجاد کیبورد منوی اصلی."""
 try:
 buttons = {
 'fa': [
 ["📚 بورسیه‌ها", "📅 تقویم تحصیلی", "🌦️ آب‌وهوا"],
 ["🔍 جستجو", "📞 تماس با ادمین", "📊 محاسبه ISEE"],
 ["👤 پروفایل", "📖 راهنما"]
 ],
 'en': [
 ["📚 Scholarships", "📅 Academic Calendar", "🌦️ Weather"],
 ["🔍 Search", "📞 Contact Admin", "📊 Calculate ISEE"],
 ["👤 Profile", "📖 Help"]
 ],
 'it': [
 ["📚 Borse di studio", "📅 Calendario accademico", "🌦️ Meteo"],
 ["🔍 Cerca", "📞 Contatta l'admin", "📊 Calcola ISEE"],
 ["👤 Profilo", "📖 Aiuto"]
 ]
 }
 keyboard = [
 [InlineKeyboardButton(text, callback_data=f"menu:{text}") for text in row]
 for row in buttons.get(lang, buttons['en'])
 ]
 return InlineKeyboardMarkup(keyboard)
 except Exception as e:
 logger.error(f"Error creating main menu keyboard: {e}")
 return InlineKeyboardMarkup([])

def get_item_keyboard(items: list, lang: str = 'fa', back_option: str = "menu:main_menu") -> InlineKeyboardMarkup:
 """ایجاد کیبورد برای آیتم‌ها با دکمه بازگشت."""
 try:
 keyboard = [
 [InlineKeyboardButton(item['title'], callback_data=f"action:{item['callback']}")]
 for item in items
 ]
 back_text = {
 'fa': "🔙 بازگشت",
 'en': "🔙 Back",
 'it': "🔙 Indietro"
 }
 keyboard.append([InlineKeyboardButton(back_text.get(lang, "🔙 Back"), callback_data=back_option)])
 return InlineKeyboardMarkup(keyboard)
 except Exception as e:
 logger.error(f"Error creating item keyboard: {e}")
 return InlineKeyboardMarkup([])
