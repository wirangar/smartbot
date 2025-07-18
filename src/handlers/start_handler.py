from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
import logging

from src.config import ADMIN_CHAT_ID
from src.services.google_sheets import append_user_data_to_sheet
from src.utils.keyboard_builder import get_main_keyboard_markup

logger = logging.getLogger(__name__)

# Conversation states
ASKING_FIRST_NAME, ASKING_LAST_NAME, ASKING_AGE, ASKING_EMAIL, MAIN_MENU = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    context.user_data['telegram_id'] = user.id
    context.user_data['registration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context.user_data['current_json_path'] = []

    welcome_message = (
        f"سلام {user.mention_html()} عزیز! 👋\n"
        "به ربات راهنمای بورسیه و زندگی دانشجویی در پروجا خوش آمدید.\n"
        "من اینجا هستم تا به شما در مسیر تحصیل و اقامت در پروجا کمک کنم.\n\n"
        "برای شروع، لطفاً نام خود را وارد کنید:"
    )
    await update.message.reply_html(welcome_message)

    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"کاربر جدید: {user.id} ({user.full_name})"
            )
        except Exception as e:
            logger.error(f"Failed to send admin notification for new user {user.id}: {e}")

    return ASKING_FIRST_NAME

async def ask_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['first_name'] = update.message.text
    await update.message.reply_text("حالا لطفاً نام خانوادگی خود را وارد کنید:")
    return ASKING_LAST_NAME

async def ask_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['last_name'] = update.message.text
    await update.message.reply_text("سن خود را به عدد وارد کنید:")
    return ASKING_AGE

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text)
        if not (0 < age < 100):
            await update.message.reply_text("لطفاً یک سن معتبر وارد کنید (بین 1 تا 99 سال).")
            return ASKING_AGE
        context.user_data['age'] = age
        await update.message.reply_text("لطفاً ایمیل خود را وارد کنید:")
        return ASKING_EMAIL
    except ValueError:
        await update.message.reply_text("سن باید یک عدد باشد. لطفاً دوباره وارد کنید:")
        return ASKING_AGE

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text
    if "@" not in email or "." not in email:
        await update.message.reply_text("لطفاً یک ایمیل معتبر وارد کنید.")
        return ASKING_EMAIL

    context.user_data['email'] = email
    if await append_user_data_to_sheet(context.user_data):
        logger.info(f"User data for {context.user_data['telegram_id']} saved to Google Sheet.")
    else:
        logger.warning(f"Could not save user data for {context.user_data['telegram_id']} to Google Sheet.")

    first_name = context.user_data.get('first_name', 'دوست')
    age = context.user_data.get('age', 'نامشخص')
    personalized_message = (
        f"عالیه، {first_name} عزیز! شما با سن {age} سال، آماده‌اید تا از خدمات ربات استفاده کنید.\n"
        "حالا می‌توانید از منوی زیر برای دسترسی به اطلاعات استفاده کنید یا سوال خود را مطرح کنید:"
    )
    await update.message.reply_text(
        personalized_message,
        reply_markup=get_main_keyboard_markup(context.user_data.get('current_json_path', []))
    )
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "مکالمه لغو شد. هر وقت نیاز داشتی دوباره می‌تونی با دستور /start شروع کنی.",
        reply_markup=get_main_keyboard_markup([])
    )
    return ConversationHandler.END
