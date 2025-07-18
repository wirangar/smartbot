from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.data.knowledge_base import get_knowledge_base

def get_main_keyboard_markup(current_path_parts: list = None) -> InlineKeyboardMarkup:
    if current_path_parts is None:
        current_path_parts = []

    keyboard = []
    kb = get_knowledge_base()

    current_level = kb
    if not current_path_parts:
        # Root level
        for category_name in kb.keys():
            keyboard.append([InlineKeyboardButton(category_name, callback_data=f"json_menu:{category_name}")])
    else:
        # Deeper levels
        for part in current_path_parts:
            if isinstance(current_level, dict):
                current_level = current_level.get(part)
            elif isinstance(current_level, list):
                current_level = next((item for item in current_level if item.get('title') == part or (item.get('fa') and item['fa'].get('title') == part)), None)

            if not current_level:
                break

        if isinstance(current_level, list):
            for item in current_level:
                title = item.get('title') or (item.get('fa') and item['fa'].get('title'))
                if title:
                    callback_data = ":".join(current_path_parts + [title])
                    keyboard.append([InlineKeyboardButton(title, callback_data=f"json_menu:{callback_data}")])

    # Add back button if not at the root
    if current_path_parts:
        back_path = ":".join(current_path_parts[:-1]) if len(current_path_parts) > 1 else "main_menu"
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"json_menu:{back_path}")])

    # Add static action buttons
    action_buttons = [
        InlineKeyboardButton("📩 ثبت سوال جدید", callback_data="action:new_question"),
        InlineKeyboardButton("📜 پاسخ‌های قبلی", callback_data="action:previous_answers"),
        InlineKeyboardButton("❓ راهنما", callback_data="action:help")
    ]
    keyboard.append(action_buttons)

    return InlineKeyboardMarkup(keyboard)
