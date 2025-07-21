from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.data.knowledge_base import get_knowledge_base

def get_language_keyboard() -> InlineKeyboardMarkup:
    """ساخت کیبورد انتخاب زبان."""
    keyboard = [
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang:fa")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang:it")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard(lang: str = 'fa') -> InlineKeyboardMarkup:
    """ساخت کیبورد منوی اصلی با گزینه‌های دسته‌بندی، جستجو و آب‌وهوا."""
    kb = get_knowledge_base()
    keyboard = []

    # آیکون‌ها برای دسته‌بندی‌ها
    category_emojis = {
        "بورسیه و تقویم آموزشی": "🎓",
        "راهنمای دانشجویی": "🏠"
    }

    # اضافه کردن دسته‌بندی‌های پایگاه دانش
    for category_name in kb.keys():
        if not isinstance(kb[category_name], list):
            continue  # نادیده گرفتن دسته‌بندی‌های نامعتبر
        emoji = category_emojis.get(category_name, "🔹")
        keyboard.append([InlineKeyboardButton(f"{emoji} {category_name}", callback_data=f"menu:{category_name}")])

    # گزینه‌های ثابت منوی اصلی
    profile_text = {"fa": "👤 پروفایل من", "en": "👤 My Profile", "it": "👤 Il Mio Profilo"}
    contact_text = {"fa": "📞 تماس با ادمین", "en": "📞 Contact Admin", "it": "📞 Contatta Admin"}
    history_text = {"fa": "📜 تاریخچه", "en": "📜 History", "it": "📜 Cronologia"}
    help_text = {"fa": "❓ راهنما", "en": "❓ Help", "it": "❓ Aiuto"}
    search_text = {"fa": "🔍 جستجو", "en": "🔍 Search", "it": "🔍 Cerca"}
    weather_text = {"fa": "🌦 آب‌وهوا", "en": "🌦 Weather", "it": "🌦 Meteo"}

    # اضافه کردن گزینه‌های ثابت و جدید (جستجو و آب‌وهوا)
    keyboard.append([
        InlineKeyboardButton(profile_text.get(lang, "👤 My Profile"), callback_data="action:profile"),
        InlineKeyboardButton(contact_text.get(lang, "📞 Contact Admin"), callback_data="action:contact_admin")
    ])
    keyboard.append([
        InlineKeyboardButton(history_text.get(lang, "📜 History"), callback_data="action:history"),
        InlineKeyboardButton(help_text.get(lang, "❓ Help"), callback_data="action:help")
    ])
    keyboard.append([
        InlineKeyboardButton(search_text.get(lang, "🔍 Search"), callback_data="action:search"),
        InlineKeyboardButton(weather_text.get(lang, "🌦 Weather"), callback_data="action:weather")
    ])

    return InlineKeyboardMarkup(keyboard)

def get_item_keyboard(category: str, lang: str = 'fa') -> InlineKeyboardMarkup:
    """ساخت کیبورد برای آیتم‌های یک دسته‌بندی."""
    kb = get_knowledge_base()
    keyboard = []

    if category in kb and isinstance(kb[category], list):
        for item in kb[category]:
            if not isinstance(item, dict):
                continue  # نادیده گرفتن آیتم‌های نامعتبر
            title = item.get('title', {}).get(lang, item.get('title', {}).get('en', 'No Title'))
            item_id = item.get('id')
            if title and item_id:
                keyboard.append([InlineKeyboardButton(title, callback_data=f"menu:{category}:{item_id}")])
    else:
        logger.warning(f"Category '{category}' not found or invalid in knowledge base.")

    # دکمه بازگشت
    back_text = {"fa": "🔙 بازگشت", "en": "🔙 Back", "it": "🔙 Indietro"}
    keyboard.append([InlineKeyboardButton(back_text.get(lang, "🔙 Back"), callback_data="menu:main_menu")])

    return InlineKeyboardMarkup(keyboard)

def get_content_keyboard(path_parts: list, lang: str = 'fa') -> InlineKeyboardMarkup:
    """ساخت کیبورد برای نمایش محتوا (دکمه‌های بازگشت)."""
    keyboard = []

    # دکمه بازگشت به لیست آیتم‌ها
    back_to_items_text = {"fa": "🔙 بازگشت به لیست", "en": "🔙 Back to List", "it": "🔙 Torna alla Lista"}
    if len(path_parts) > 1:
        keyboard.append([InlineKeyboardButton(back_to_items_text.get(lang, "🔙 Back to List"), callback_data=f"menu:{path_parts[0]}")])

    # دکمه بازگشت به منوی اصلی
    back_to_main_text = {"fa": "🏠 بازگشت به منوی اصلی", "en": "🏠 Back to Main Menu", "it": "🏠 Torna al Menu Principale"}
    keyboard.append([InlineKeyboardButton(back_to_main_text.get(lang, "🏠 Back to Main Menu"), callback_data="menu:main_menu")])

    return InlineKeyboardMarkup(keyboard)
