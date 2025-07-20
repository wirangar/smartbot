import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from src.database import get_db_cursor
from src.utils.keyboard_builder import get_language_keyboard, get_main_menu_keyboard
from src.config import logger, ADMIN_CHAT_ID
from src.locale import get_message
from src.utils.text_formatter import sanitize_markdown

# Conversation states
SELECTING_LANG, ASKING_FIRST_NAME, ASKING_LAST_NAME, ASKING_AGE, ASKING_EMAIL, MAIN_MENU = range(6)

# --- Onboarding and Registration ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for language selection."""
    user_id = update.effective_user.id

    # Check if user already exists
    with get_db_cursor() as cursor:
        cursor.execute("SELECT language FROM users WHERE telegram_id = %s", (user_id,))
        user_record = cursor.fetchone()

    if user_record:
        lang = user_record[0]
        context.user_data['language'] = lang
        welcome_back_text = get_message("welcome_back", lang)
        await update.message.reply_text(
            welcome_back_text,
            reply_markup=get_main_menu_keyboard(lang)
        )
        return MAIN_MENU

    # New user
    welcome_text = (
        "🇮🇷 به ربات Scholarino خوش آمدید!\n"
        "این ربات راهنمای شما برای زندگی و تحصیل در پروجا است. لطفاً زبان خود را انتخاب کنید.\n\n"
        "🇬🇧 Welcome to the Scholarino Bot!\n"
        "This bot is your guide to living and studying in Perugia. Please select your language.\n\n"
        "🇮🇹 Benvenuto nel Bot Scholarino!\n"
        "Questo bot è la tua guida per vivere e studiare a Perugia. Seleziona la tua lingua."
    )
    await update.message.reply_text(welcome_text, reply_markup=get_language_keyboard())
    return SELECTING_LANG

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the selected language and asks for the first name."""
    query = update.callback_query
    await query.answer()

    lang = query.data.split(":")[1]
    context.user_data['language'] = lang

    await query.edit_message_text(text=get_message("ask_first_name", lang))
    return ASKING_FIRST_NAME

async def ask_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['first_name'] = update.message.text
    lang = context.user_data.get('language', 'fa')
    await update.message.reply_text(get_message("ask_last_name", lang))
    return ASKING_LAST_NAME

async def ask_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['last_name'] = update.message.text
    lang = context.user_data.get('language', 'fa')
    await update.message.reply_text(get_message("ask_age", lang))
    return ASKING_AGE

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get('language', 'fa')
    try:
        age = int(update.message.text)
        if not (10 < age < 90):
            raise ValueError("Invalid age")
        context.user_data['age'] = age
        await update.message.reply_text(get_message("ask_email", lang))
        return ASKING_EMAIL
    except ValueError:
        await update.message.reply_text(get_message("invalid_age", lang))
        return ASKING_AGE

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves all user data to the database and shows the main menu."""
    email = update.message.text
    lang = context.user_data.get('language', 'fa')
    if "@" not in email or "." not in email:
        await update.message.reply_text(get_message("invalid_email", lang))
        return ASKING_EMAIL

    context.user_data['email'] = email
    user_id = update.effective_user.id

    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (telegram_id, first_name, last_name, age, email, language)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    age = EXCLUDED.age,
                    email = EXCLUDED.email,
                    language = EXCLUDED.language;
                """,
                (user_id, context.user_data['first_name'], context.user_data['last_name'], context.user_data['age'], email, lang)
            )
        logger.info(f"User {user_id} registered/updated successfully.")

        if ADMIN_CHAT_ID:
            admin_notification = get_message("admin_new_user_notification", 'en', id=user_id, name=f"{context.user_data['first_name']} {context.user_data['last_name']}", age=context.user_data['age'], email=email, lang=lang)
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_notification)

    except Exception as e:
        logger.error(f"Failed to save user {user_id} to database: {e}")
        await update.message.reply_text(get_message("db_error", lang))
        return ConversationHandler.END

    await update.message.reply_text(get_message("registration_success", lang), reply_markup=get_main_menu_keyboard(lang))
    return MAIN_MENU

async def show_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Command handler for /profile."""
    await show_profile(update, context, is_command=True)
    return MAIN_MENU

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, is_command: bool = False):
    """Displays the user's profile information."""
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'fa')

    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT first_name, last_name, age, email, score FROM users WHERE telegram_id = %s", (user_id,))
            user_data = cursor.fetchone()

        if user_data:
            first_name, last_name, age, email, score = user_data
            profile_text = get_message("profile_text", lang, first_name=first_name, last_name=last_name, age=age, email=email, score=score)
        else:
            profile_text = get_message("profile_not_found", lang)

        sanitized_text = sanitize_markdown(profile_text)

        if is_command:
            await update.message.reply_text(sanitized_text, parse_mode='MarkdownV2', reply_markup=get_main_menu_keyboard(lang))
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(sanitized_text, parse_mode='MarkdownV2', reply_markup=get_main_menu_keyboard(lang))

    except Exception as e:
        logger.error(f"Failed to fetch profile for user {user_id}: {e}")
        error_text = get_message("profile_error", lang)
        if is_command:
            await update.message.reply_text(error_text, reply_markup=get_main_menu_keyboard(lang))
        else:
            await update.callback_query.edit_message_text(error_text, reply_markup=get_main_menu_keyboard(lang))

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user if they want to subscribe to notifications."""
    lang = context.user_data.get('language', 'fa')

    keyboard = [[
        InlineKeyboardButton(get_message("yes", lang), callback_data="subscribe:yes"),
        InlineKeyboardButton(get_message("no", lang), callback_data="subscribe:no")
    ]]

    await update.message.reply_text(get_message("subscribe_prompt", lang), reply_markup=InlineKeyboardMarkup(keyboard))
    return MAIN_MENU

async def handle_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the subscription choice."""
    query = update.callback_query
    await query.answer()
    choice = query.data.split(":")[1]
    user_id = query.from_user.id
    lang = context.user_data.get('language', 'fa')

    subscribe_status = True if choice == 'yes' else False

    try:
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE users SET is_subscribed_to_notifications = %s WHERE telegram_id = %s", (subscribe_status, user_id))

        response_text = get_message("subscribe_success" if subscribe_status else "unsubscribe_success", lang)
        await query.edit_message_text(text=response_text)

    except Exception as e:
        logger.error(f"Failed to update subscription status for user {user_id}: {e}")
        await query.edit_message_text(text=get_message("subscribe_error", lang))

    await query.message.reply_text(text=get_message("main_menu_prompt", lang), reply_markup=get_main_menu_keyboard(lang))
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the current conversation."""
    lang = context.user_data.get('language', 'fa')
    await update.message.reply_text(get_message("operation_cancelled", lang))
    return ConversationHandler.END
