from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data.knowledge_base import get_knowledge_base

def get_main_keyboard_markup(path_parts: list = None, lang: str = 'fa') -> InlineKeyboardMarkup:
    if path_parts is None:
        path_parts = []

    keyboard = []
    kb = get_knowledge_base()

    if not path_parts:
        # Level 0: Show main categories
        for category_name in kb.keys():
            keyboard.append([InlineKeyboardButton(category_name, callback_data=f"menu:{category_name}")])

    elif len(path_parts) == 1:
        # Level 1: Show items in a category
        category_key = path_parts[0]
        if category_key in kb:
            for item in kb[category_key]:
                title = item.get('title', {}).get(lang, 'No Title')
                item_id = item.get('id')
                if title and item_id:
                    keyboard.append([InlineKeyboardButton(title, callback_data=f"menu:{category_key}:{item_id}")])

    # Back button logic
    if path_parts:
        back_path = ":".join(path_parts[:-1])
        if not back_path:
            back_path = "main_menu"
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"menu:{back_path}")])

    # Static action buttons
    action_buttons = [
        InlineKeyboardButton("📩 تماس با ادمین", callback_data="action:contact_admin"),
        InlineKeyboardButton("📜 پاسخ‌های قبلی", callback_data="action:previous_answers"),
        InlineKeyboardButton("❓ راهنما", callback_data="action:help")
    ]
    keyboard.append(action_buttons)

    return InlineKeyboardMarkup(keyboard)
