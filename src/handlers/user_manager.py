import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from src.database import get_db_cursor
from src.utils.keyboard_builder import get_language_keyboard, get_main_menu_keyboard
from src.config import logger

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
        welcome_back_text = {
            'fa': "سلام مجدد! به منوی اصلی خوش آمدید.",
            'en': "Welcome back! Here is the main menu.",
            'it': "Bentornato! Ecco il menu principale."
        }
        await update.message.reply_text(
            welcome_back_text.get(lang, "Welcome back!"),
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

    prompt_text = {
        'fa': "عالی! برای شروع، لطفاً نام خود را وارد کنید:",
        'en': "Great! To get started, please enter your first name:",
        'it': "Ottimo! Per iniziare, inserisci il tuo nome:"
    }
    await query.edit_message_text(text=prompt_text.get(lang))
    return ASKING_FIRST_NAME

async def ask_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['first_name'] = update.message.text
    lang = context.user_data.get('language', 'fa')
    prompt_text = {
        'fa': "متشکرم. اکنون نام خانوادگی خود را وارد کنید:",
        'en': "Thank you. Now, please enter your last name:",
        'it': "Grazie. Ora, inserisci il tuo cognome:"
    }
    await update.message.reply_text(prompt_text.get(lang))
    return ASKING_LAST_NAME

async def ask_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['last_name'] = update.message.text
    lang = context.user_data.get('language', 'fa')
    prompt_text = {
        'fa': "لطفاً سن خود را به عدد وارد کنید:",
        'en': "Please enter your age as a number:",
        'it': "Inserisci la tua età come numero:"
    }
    await update.message.reply_text(prompt_text.get(lang))
    return ASKING_AGE

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get('language', 'fa')
    try:
        age = int(update.message.text)
        if not (10 < age < 90):
            raise ValueError("Invalid age")
        context.user_data['age'] = age
        prompt_text = {'fa': "و در آخر، ایمیل خود را وارد کنید:", 'en': "Finally, please enter your email:", 'it': "Infine, inserisci la tua email:"}
        await update.message.reply_text(prompt_text.get(lang))
        return ASKING_EMAIL
    except ValueError:
        error_text = {'fa': "سن نامعتبر است. لطفاً دوباره یک عدد وارد کنید.", 'en': "Invalid age. Please enter a number again.", 'it': "Età non valida. Inserisci di nuovo un numero."}
        await update.message.reply_text(error_text.get(lang))
        return ASKING_AGE

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves all user data to the database and shows the main menu."""
    email = update.message.text
    lang = context.user_data.get('language', 'fa')
    if "@" not in email or "." not in email:
        error_text = {'fa': "ایمیل نامعتبر است. لطفاً دوباره وارد کنید.", 'en': "Invalid email. Please enter it again.", 'it': "Email non valida. Inseriscila di nuovo."}
        await update.message.reply_text(error_text.get(lang))
        return ASKING_EMAIL

    context.user_data['email'] = email
    user_id = update.effective_user.id

    # Save to database
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
    except Exception as e:
        logger.error(f"Failed to save user {user_id} to database: {e}")
        # Handle error gracefully
        error_text = {'fa': "مشکلی در ذخیره اطلاعات شما رخ داد. لطفاً بعداً دوباره امتحان کنید.", 'en': "An error occurred while saving your information. Please try again later.", 'it': "Si è verificato un errore durante il salvataggio delle informazioni. Riprova più tardi."}
        await update.message.reply_text(error_text.get(lang))
        return ConversationHandler.END

    success_text = {'fa': "✅ ثبت‌نام شما با موفقیت انجام شد! به منوی اصلی خوش آمدید.", 'en': "✅ Registration complete! Welcome to the main menu.", 'it': "✅ Registrazione completata! Benvenuto nel menu principale."}
    await update.message.reply_text(success_text.get(lang), reply_markup=get_main_menu_keyboard(lang))
    return MAIN_MENU

async def show_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Command handler for /profile."""
    await show_profile(update, context, is_command=True)
    return MAIN_MENU

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, is_command: bool = False) -> int:
    """Displays the user's profile information."""
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'fa')

    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT first_name, last_name, age, email, score FROM users WHERE telegram_id = %s", (user_id,))
            user_data = cursor.fetchone()

        if user_data:
            first_name, last_name, age, email, score = user_data
            profile_text_map = {
                'fa': f"👤 *پروفایل شما*\n\n*نام:* {first_name}\n*نام خانوادگی:* {last_name}\n*سن:* {age}\n*ایمیل:* {email}\n*امتیاز:* {score} ✨",
                'en': f"👤 *Your Profile*\n\n*First Name:* {first_name}\n*Last Name:* {last_name}\n*Age:* {age}\n*Email:* {email}\n*Score:* {score} ✨",
                'it': f"👤 *Il Tuo Profilo*\n\n*Nome:* {first_name}\n*Cognome:* {last_name}\n*Età:* {age}\n*Email:* {email}\n*Punteggio:* {score} ✨"
            }
            profile_text = profile_text_map.get(lang)
        else:
            not_found_text_map = {'fa': "اطلاعات پروفایل شما یافت نشد. لطفاً با /start ثبت‌نام کنید.", 'en': "Your profile information was not found. Please register with /start.", 'it': "Le tue informazioni del profilo non sono state trovate. Registrati con /start."}
            profile_text = not_found_text_map.get(lang)

        if is_command:
            await update.message.reply_text(profile_text, parse_mode='Markdown', reply_markup=get_main_menu_keyboard(lang))
        else:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(profile_text, parse_mode='Markdown', reply_markup=get_main_menu_keyboard(lang))

    except Exception as e:
        logger.error(f"Failed to fetch profile for user {user_id}: {e}")
        error_text_map = {'fa': "خطایی در دریافت اطلاعات پروفایل رخ داد.", 'en': "An error occurred while fetching your profile.", 'it': "Si è verificato un errore durante il recupero del tuo profilo."}
        error_text = error_text_map.get(lang)
        if is_command:
            await update.message.reply_text(error_text, reply_markup=get_main_menu_keyboard(lang))
        else:
            await update.callback_query.edit_message_text(error_text, reply_markup=get_main_menu_keyboard(lang))

    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the current conversation."""
    lang = context.user_data.get('language', 'fa')
    cancel_text = {'fa': "عملیات لغو شد.", 'en': "Operation cancelled.", 'it': "Operazione annullata."}
    await update.message.reply_text(cancel_text.get(lang), reply_markup=get_main_menu_keyboard(lang))
    return ConversationHandler.END
