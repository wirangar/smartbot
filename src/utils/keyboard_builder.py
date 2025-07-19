from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.data.knowledge_base import get_knowledge_base
from src.locale import get_message

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Returns the language selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang:fa")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang:it")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard(lang: str = 'fa') -> InlineKeyboardMarkup:
    """Returns the main menu keyboard with top-level actions."""
    kb = get_knowledge_base()
    keyboard = []

    # Dynamic categories from knowledge base
    category_emojis = {"بورسیه و تقویم آموزشی": "🎓", "راهنمای دانشجویی": "🏠"}
    for category_name in kb.keys():
        emoji = category_emojis.get(category_name, "🔹")
        keyboard.append([InlineKeyboardButton(f"{emoji} {category_name}", callback_data=f"menu:{category_name}")])

    # Static feature buttons
    keyboard.append([
        InlineKeyboardButton(get_message("isee_button", lang), callback_data="action:start_isee"),
        InlineKeyboardButton(get_message("search_button", lang), callback_data="action:start_search")
    ])

    # Static action buttons at the bottom
    keyboard.append([
        InlineKeyboardButton(get_message("profile_button", lang), callback_data="action:profile"),
        InlineKeyboardButton(get_message("weather_button", lang), callback_data="action:weather")
    ])
    keyboard.append([
        InlineKeyboardButton(get_message("contact_button", lang), callback_data="action:contact_admin"),
        InlineKeyboardButton(get_message("help_button", lang), callback_data="action:help")
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
    keyboard.append([InlineKeyboardButton(get_message("back_button", lang), callback_data="menu:main_menu")])

    return InlineKeyboardMarkup(keyboard)

def get_content_keyboard(path_parts: list, lang: str = 'fa') -> InlineKeyboardMarkup:
    """Returns a keyboard for the content view (back buttons)."""
    keyboard = []

    # Back to item list
    if len(path_parts) > 1:
        keyboard.append([InlineKeyboardButton(get_message("back_to_list_button", lang), callback_data=f"menu:{path_parts[0]}")])

    # Back to main menu
    keyboard.append([InlineKeyboardButton(get_message("back_to_main_menu_button", lang), callback_data="menu:main_menu")])

    return InlineKeyboardMarkup(keyboard)
