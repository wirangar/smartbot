from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.config import logger
from src.utils.text_formatter import sanitize_markdown

def get_main_menu_keyboard(lang: str = 'fa') -> InlineKeyboardMarkup:
    """ایجاد کیبورد منوی اصلی."""
    try:
        buttons = {
            'fa': [
                [
                    InlineKeyboardButton("📚 بورسیه‌ها", callback_data="menu:scholarships"),
                    InlineKeyboardButton("📅 تقویم تحصیلی", callback_data="menu:calendar"),
                    InlineKeyboardButton("🌦️ آب‌وهوا", callback_data="menu:weather")
                ],
                [
                    InlineKeyboardButton("🔍 جستجو", callback_data="action:search"),
                    InlineKeyboardButton("📞 تماس با ادمین", callback_data="action:contact_admin"),
                    InlineKeyboardButton("📊 محاسبه ISEE", callback_data="action:isee")
                ],
                [
                    InlineKeyboardButton("👤 پروفایل", callback_data="menu:profile"),
                    InlineKeyboardButton("📖 راهنما", callback_data="menu:help"),
                    InlineKeyboardButton("🌐 تغییر زبان", callback_data="menu:change_language")
                ]
            ],
            'en': [
                [
                    InlineKeyboardButton("📚 Scholarships", callback_data="menu:scholarships"),
                    InlineKeyboardButton("📅 Academic Calendar", callback_data="menu:calendar"),
                    InlineKeyboardButton("🌦️ Weather", callback_data="menu:weather")
                ],
                [
                    InlineKeyboardButton("🔍 Search", callback_data="action:search"),
                    InlineKeyboardButton("📞 Contact Admin", callback_data="action:contact_admin"),
                    InlineKeyboardButton("📊 Calculate ISEE", callback_data="action:isee")
                ],
                [
                    InlineKeyboardButton("👤 Profile", callback_data="menu:profile"),
                    InlineKeyboardButton("📖 Help", callback_data="menu:help"),
                    InlineKeyboardButton("🌐 Change Language", callback_data="menu:change_language")
                ]
            ],
            'it': [
                [
                    InlineKeyboardButton("📚 Borse di studio", callback_data="menu:scholarships"),
                    InlineKeyboardButton("📅 Calendario accademico", callback_data="menu:calendar"),
                    InlineKeyboardButton("🌦️ Meteo", callback_data="menu:weather")
                ],
                [
                    InlineKeyboardButton("🔍 Cerca", callback_data="action:search"),
                    InlineKeyboardButton("📞 Contatta l'admin", callback_data="action:contact_admin"),
                    InlineKeyboardButton("📊 Calcola ISEE", callback_data="action:isee")
                ],
                [
                    InlineKeyboardButton("👤 Profilo", callback_data="menu:profile"),
                    InlineKeyboardButton("📖 Aiuto", callback_data="menu:help"),
                    InlineKeyboardButton("🌐 Cambia Lingua", callback_data="menu:change_language")
                ]
            ]
        }
        return InlineKeyboardMarkup(buttons.get(lang, buttons['fa']))
    except Exception as e:
        logger.error(f"Error creating main menu keyboard: {e}")
        return InlineKeyboardMarkup([])

def get_item_keyboard(items: list, lang: str = 'fa', back_option: str = "menu:main_menu") -> InlineKeyboardMarkup:
    """ایجاد کیبورد برای آیتم‌ها با دکمه بازگشت."""
    try:
        keyboard = [
            [InlineKeyboardButton(sanitize_markdown(item['title']), callback_data=item['callback'])]
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
