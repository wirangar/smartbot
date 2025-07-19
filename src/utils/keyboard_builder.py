from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.data.knowledge_base import get_knowledge_base

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Returns the language selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang:fa")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang:it")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard(lang: str = 'fa') -> InlineKeyboardMarkup:
    """Returns the main menu keyboard."""
    kb = get_knowledge_base()
    keyboard = []

    # Main categories
    for category_name in kb.keys():
        # For now, we assume category names are the keys themselves.
        # This can be improved by adding a title field to categories in JSON.
        keyboard.append([InlineKeyboardButton(f"🔹 {category_name}", callback_data=f"menu:{category_name}")])

    # Static action buttons at the bottom
    # These should be translated based on the 'lang' parameter.
    profile_text = {"fa": "👤 پروفایل من", "en": "👤 My Profile", "it": "👤 Il Mio Profilo"}
    contact_text = {"fa": "📞 تماس با ادمین", "en": "📞 Contact Admin", "it": "📞 Contatta Admin"}
    history_text = {"fa": "📜 تاریخچه", "en": "📜 History", "it": "📜 Cronologia"}
    help_text = {"fa": "❓ راهنما", "en": "❓ Help", "it": "❓ Aiuto"}

    keyboard.append([
        InlineKeyboardButton(profile_text.get(lang, "👤 My Profile"), callback_data="action:profile"),
        InlineKeyboardButton(contact_text.get(lang, "📞 Contact Admin"), callback_data="action:contact_admin")
    ])
    keyboard.append([
        InlineKeyboardButton(history_text.get(lang, "📜 History"), callback_data="action:history"),
        InlineKeyboardButton(help_text.get(lang, "❓ Help"), callback_data="action:help")
    ])

    return InlineKeyboardMarkup(keyboard)

def get_item_keyboard(category: str, lang: str = 'fa') -> InlineKeyboardMarkup:
    """Returns a keyboard for items within a category."""
    kb = get_knowledge_base()
    keyboard = []

    if category in kb:
        for item in kb[category]:
            title = item.get('title', {}).get(lang, 'No Title')
            item_id = item.get('id')
            if title and item_id:
                keyboard.append([InlineKeyboardButton(title, callback_data=f"menu:{category}:{item_id}")])

    # Back button
    back_text = {"fa": "🔙 بازگشت", "en": "🔙 Back", "it": "🔙 Indietro"}
    keyboard.append([InlineKeyboardButton(back_text.get(lang, "🔙 Back"), callback_data="menu:main_menu")])

    return InlineKeyboardMarkup(keyboard)

def get_content_keyboard(path_parts: list, lang: str = 'fa') -> InlineKeyboardMarkup:
    """Returns a keyboard for the content view (back buttons)."""
    keyboard = []

    # Back to item list
    back_to_items_text = {"fa": "🔙 بازگشت به لیست", "en": "🔙 Back to List", "it": "🔙 Torna alla Lista"}
    if len(path_parts) > 1:
        keyboard.append([InlineKeyboardButton(back_to_items_text.get(lang, "🔙 Back to List"), callback_data=f"menu:{path_parts[0]}")])

    # Back to main menu
    back_to_main_text = {"fa": "🏠 بازگشت به منوی اصلی", "en": "🏠 Back to Main Menu", "it": "🏠 Torna al Menu Principale"}
    keyboard.append([InlineKeyboardButton(back_to_main_text.get(lang, "🏠 Back to Main Menu"), callback_data="menu:main_menu")])

    return InlineKeyboardMarkup(keyboard)
