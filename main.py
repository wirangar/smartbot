import logging
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
import openai
from datetime import datetime
from flask import Request
from functions_framework import http
import asyncio
import threading

# --- Define Conversation States ---
ASKING_FIRST_NAME, ASKING_LAST_NAME, ASKING_AGE, ASKING_EMAIL, MAIN_MENU = range(5)

# --- Load Environment Variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 8080))
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")  # Path to credentials file
SHEET_ID = os.getenv("SHEET_ID")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))
SCHOLARSHIPS_SHEET_NAME = "Scholarship"
BAZARINO_ORDERS_SHEET_NAME = "Bazarino Orders"

# --- Set up Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Log Environment Variables for Debugging ---
logger.info(f"TELEGRAM_TOKEN: {'Set' if TELEGRAM_BOT_TOKEN else 'Not set'}")
logger.info(f"OPENAI_API_KEY: {'Set' if OPENAI_API_KEY else 'Not set'}")
logger.info(f"WEBHOOK_SECRET: {'Set' if WEBHOOK_SECRET else 'Not set'}")
logger.info(f"BASE_URL: {BASE_URL}")
logger.info(f"PORT: {PORT}")
logger.info(f"GOOGLE_CREDS: {GOOGLE_CREDS}")
logger.info(f"SHEET_ID: {SHEET_ID}")
logger.info(f"ADMIN_CHAT_ID: {ADMIN_CHAT_ID}")

# --- Initialize OpenAI client ---
openai.api_key = OPENAI_API_KEY

# --- Google Sheets Setup ---
gc = None
scholarships_sheet = None
bazarino_orders_sheet = None

def init_google_sheets():
    global gc, scholarships_sheet, bazarino_orders_sheet
    try:
        if not GOOGLE_CREDS:
            logger.warning("GOOGLE_CREDS not set. Google Sheets functionality will be disabled.")
            return
        if not os.path.exists(GOOGLE_CREDS):
            logger.error(f"Credentials file not found at {GOOGLE_CREDS}")
            return
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS, scope)
        gc = gspread.authorize(creds)
        
        spreadsheet = gc.open_by_key(SHEET_ID)
        try:
            scholarships_sheet = spreadsheet.worksheet(SCHOLARSHIPS_SHEET_NAME)
            expected_columns = ['telegram_id', 'first_name', 'last_name', 'age', 'email', 'language', 'registration_date']
            actual_columns = scholarships_sheet.row_values(1)
            if actual_columns != expected_columns:
                logger.warning(f"Scholarship sheet columns mismatch. Expected: {expected_columns}, Found: {actual_columns}")
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{SCHOLARSHIPS_SHEET_NAME}' not found in spreadsheet {SHEET_ID}")
            scholarships_sheet = None
        
        try:
            bazarino_orders_sheet = spreadsheet.worksheet(BAZARINO_ORDERS_SHEET_NAME)
            expected_columns = ['telegram_id', 'question', 'answer', 'timestamp']
            actual_columns = bazarino_orders_sheet.row_values(1)
            if actual_columns != expected_columns:
                logger.warning(f"Bazarino Orders sheet columns mismatch. Expected: {expected_columns}, Found: {actual_columns}")
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{BAZARINO_ORDERS_SHEET_NAME}' not found in spreadsheet {SHEET_ID}")
            bazarino_orders_sheet = None
            
        if scholarships_sheet and bazarino_orders_sheet:
            logger.info("Google Sheets initialized successfully.")
        else:
            logger.warning("One or more worksheets could not be initialized.")
    except Exception as e:
        logger.error(f"Error initializing Google Sheets: {str(e)}")
        gc = None
        scholarships_sheet = None
        bazarino_orders_sheet = None

init_google_sheets()

async def append_user_data_to_sheet(user_data: dict) -> bool:
    if scholarships_sheet:
        try:
            row = [
                user_data.get('telegram_id', ''),
                user_data.get('first_name', ''),
                user_data.get('last_name', ''),
                user_data.get('age', ''),
                user_data.get('email', ''),
                user_data.get('language', 'fa'),
                user_data.get('registration_date', '')
            ]
            scholarships_sheet.append_row(row)
            logger.info(f"User data appended to Google Sheet: {user_data}")
            return True
        except Exception as e:
            logger.error(f"Failed to append user data to Google Sheet: {e}")
            return False
    else:
        logger.warning("Google Sheet (Scholarship) not initialized. Cannot append user data.")
        return False

async def append_qa_to_sheet(telegram_id: int, question: str, answer: str) -> bool:
    if bazarino_orders_sheet:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [telegram_id, question, answer, timestamp]
            bazarino_orders_sheet.append_row(row)
            logger.info(f"Q&A appended to Google Sheet for user {telegram_id}.")
            return True
        except Exception as e:
            logger.error(f"Failed to append Q&A to Google Sheet: {e}")
            return False
    else:
        logger.warning("Google Sheet (Bazarino Orders) not initialized. Cannot append Q&A.")
        return False

async def get_previous_answers(telegram_id: int) -> str:
    if bazarino_orders_sheet:
        try:
            records = bazarino_orders_sheet.get_all_records()
            user_answers = [
                f"سوال: {record['question']}\nپاسخ: {record['answer']}\nزمان: {record['timestamp']}"
                for record in records if str(record['telegram_id']) == str(telegram_id)
            ]
            if user_answers:
                return "\n\n".join(user_answers)
            else:
                return "هیچ سوال و پاسخی برای شما ثبت نشده است."
        except Exception as e:
            logger.error(f"Error fetching previous answers: {e}")
            return "خطایی در دریافت پاسخ‌های قبلی رخ داد."
    else:
        return "قابلیت نمایش پاسخ‌های قبلی در دسترس نیست."

# --- Load Knowledge Base from JSON ---
KNOWLEDGE_FILE = 'knowledge.json'
knowledge_base = {}

def load_knowledge_base():
    global knowledge_base
    try:
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
        logger.info(f"Knowledge base '{KNOWLEDGE_FILE}' loaded successfully.")
    except FileNotFoundError:
        logger.error(f"Knowledge base file '{KNOWLEDGE_FILE}' not found.")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from '{KNOWLEDGE_FILE}'.")

load_knowledge_base()

# --- System Prompt ---
SYSTEM_PROMPT = """
تو یک ربات هوش مصنوعی هستی که فقط در مورد بورسیه‌های دانشجویی و زندگی دانشجویی در شهر پروجا، ایتالیا اطلاعات ارائه می‌دهی.
پاسخ‌هایت را به زبان فارسی بده.
اگر اطلاعات مشخص و دقیقی در مورد سوال کاربر در دانش داخلی‌ات یا متنی که به تو داده می‌شود وجود دارد، از همان اطلاعات استفاده کن و به هیچ عنوان از آن منحرف نشو.
اگر سوالی خارج از این موضوع (بورسیه‌های دانشجویی و زندگی در پروجا) از تو پرسیده شد، مودبانه و به فارسی بگو که فقط در مورد بورسیه‌های دانشجویی و زندگی در پروجا می‌توانی کمک کنی و نمی‌توانی به سوالات دیگر پاسخ دهی.
اطلاعاتی که می‌دهی باید بر اساس داده‌های عمومی و موجود در مورد بورسیه‌های پروجا و زندگی دانشجویی باشد.
مهم: هرگز خارج از حوزه بورسیه‌های دانشجویی و زندگی در پروجا پاسخ نده.
"""

def get_json_content_by_path(path_parts: list) -> str:
    current_level = knowledge_base
    content = ""
    try:
        for i, part in enumerate(path_parts):
            if isinstance(current_level, dict):
                current_level = current_level.get(part)
                if not current_level: return ""  # Category not found
            elif isinstance(current_level, list):
                found_item = None
                for item in current_level:
                    title = item.get('title')
                    if not title and 'fa' in item and 'title' in item['fa']:
                        title = item['fa']['title']
                    if title == part:
                        found_item = item
                        break
                if not found_item: return ""  # Item not found
                current_level = found_item

            if i == len(path_parts) - 1:
                if 'fa' in current_level:
                    if 'content' in current_level['fa']:
                        content = current_level['fa']['content']
                    elif 'description' in current_level['fa']:
                        content = current_level['fa']['description']
                        if current_level['fa'].get('details'):
                            content += "\n" + "\n".join(current_level['fa']['details'])
                        if current_level['fa'].get('steps'):
                            steps_content = []
                            for step in current_level['fa']['steps']:
                                step_title = step.get('title', '')
                                if 'content' in step:
                                    steps_content.append(f"{step_title}: {step['content']}")
                                elif 'items' in step:
                                    steps_content.append(f"{step_title}:\n" + "\n".join([f"- {i}" for i in step['items']]))
                            content += "\nمراحل:\n" + "\n".join(steps_content)
                    elif 'items' in current_level['fa'] and isinstance(current_level['fa']['items'], list):
                        if all(isinstance(i, str) for i in current_level['fa']['items']):
                            content = "موارد: \n" + "\n".join([f"- {i}" for i in current_level['fa']['items']])
                        elif all(isinstance(i, dict) and 'مورد' in i for i in current_level['fa']['items']):
                            change_details = []
                            for change in current_level['fa']['items']:
                                change_details.append(f"مورد: {change.get('مورد')}\n  سال قبل: {change.get('سال قبل')}\n  امسال: {change.get('امسال')}\n  توضیح: {change.get('توضیح')}")
                            content = "تغییرات:\n" + "\n".join(change_details)
                        elif 'dates' in current_level['fa'] and isinstance(current_level['fa']['dates'], list):
                            dates_content = []
                            for date_item in current_level['fa']['dates']:
                                dates_content.append(f"{date_item.get('event')}: {date_item.get('deadline')}")
                            content = "ددلاین‌ها:\n" + "\n".join(dates_content)
                        elif 'apps' in current_level['fa'] and isinstance(current_level['fa']['apps'], list):
                            apps_content = []
                            for app in current_level['fa']['apps']:
                                apps_content.append(f"اپلیکیشن: {app.get('name')}\n  توضیح: {app.get('description')}\n  لینک: {app.get('link')}")
                            content = "اپلیکیشن‌ها:\n" + "\n".join(apps_content)
                
                if not content and 'content' in current_level:
                    content = current_level['content']
                elif not content and 'points' in current_level:
                    content = "\n".join(current_level['points'])
                
        return content
    except Exception as e:
        logger.error(f"Error navigating JSON path {path_parts}: {e}")
        return ""

def get_main_keyboard_markup(current_path_parts: list = None) -> InlineKeyboardMarkup:
    if current_path_parts is None:
        current_path_parts = []

    keyboard = []
    
    if not current_path_parts:
        for category_name in knowledge_base.keys():
            keyboard.append([InlineKeyboardButton(category_name, callback_data=f"json_menu:{category_name}")])
    else:
        current_level = knowledge_base
        for i, part in enumerate(current_path_parts):
            if isinstance(current_level, dict):
                if i == 0:
                    current_level = current_level.get(part)
                else:
                    found_item = None
                    for item in current_level:
                        title = item.get('title')
                        if not title and 'fa' in item and 'title' in item['fa']:
                            title = item['fa']['title']
                        if title == part:
                            found_item = item
                            break
                    current_level = found_item
                if not current_level: break

        if isinstance(current_level, list):
            for item in current_level:
                title = item.get('title')
                if not title and 'fa' in item and 'title' in item['fa']:
                    title = item['fa']['title']
                if title:
                    callback_data = ":".join(current_path_parts + [title])
                    keyboard.append([InlineKeyboardButton(title, callback_data=f"json_menu:{callback_data}")])

    if current_path_parts:
        back_path = ":".join(current_path_parts[:-1]) if len(current_path_parts) > 1 else "main_menu"
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"json_menu:{back_path}")])
    
    action_buttons = [
        InlineKeyboardButton("📩 ثبت سوال جدید", callback_data="action:new_question"),
        InlineKeyboardButton("📜 پاسخ‌های قبلی", callback_data="action:previous_answers"),
        InlineKeyboardButton("❓ راهنما", callback_data="action:help")
    ]
    keyboard.append(action_buttons)

    return InlineKeyboardMarkup(keyboard)

# --- Handlers for Conversation Flow ---
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
            logger.error(f"Failed to send admin notification: {e}")
    
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
    else:
        context.user_data['email'] = email
        if await append_user_data_to_sheet(context.user_data):
            logger.info("User data successfully saved to Google Sheet.")
        else:
            logger.warning("Could not save user data to Google Sheet.")
        
        first_name = context.user_data.get('first_name', 'دوست')
        age = context.user_data.get('age', 'نامشخص')
        personalized_message = (
            f"عالیه، {first_name} عزیز! شما با سن {age} سال، آماده‌اید تا از خدمات ربات استفاده کنید.\n"
            "حالا می‌توانید از منوی زیر برای دسترسی به اطلاعات استفاده کنید یا سوال خود را مطرح کنید:"
        )
        await update.message.reply_text(personalized_message, reply_markup=get_main_keyboard_markup(context.user_data['current_json_path']))
        return MAIN_MENU

async def handle_json_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    path_indicator = data[1] if len(data) > 1 else ""

    if path_indicator == "main_menu":
        context.user_data['current_json_path'] = []
    else:
        context.user_data['current_json_path'] = data[1:]

    current_path_parts = context.user_data['current_json_path']
    content_to_display = get_json_content_by_path(current_path_parts)
    
    if content_to_display:
        await query.edit_message_text(content_to_display, reply_markup=get_main_keyboard_markup(current_path_parts))
    else:
        message_text = "لطفاً یک گزینه را انتخاب کنید:"
        if not current_path_parts:
            message_text = "لطفاً یک دسته را انتخاب کنید یا سوال خود را مطرح کنید:"
        await query.edit_message_text(message_text, reply_markup=get_main_keyboard_markup(current_path_parts))
    
    return MAIN_MENU

async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1]

    if action == "new_question":
        context.user_data['current_json_path'] = []
        await query.edit_message_text(
            "لطفاً سوال جدید خود را مطرح کنید. من تلاش می‌کنم با هوش مصنوعی به آن پاسخ دهم.\n"
            "برای بازگشت به منوها می‌توانید دکمه‌های زیر را انتخاب کنید:",
            reply_markup=get_main_keyboard_markup(context.user_data['current_json_path'])
        )
    elif action == "previous_answers":
        telegram_id = update.effective_user.id
        previous_answers = await get_previous_answers(telegram_id)
        await query.edit_message_text(
            previous_answers,
            reply_markup=get_main_keyboard_markup(context.user_data['current_json_path'])
        )
    elif action == "help":
        await query.edit_message_text(
            "من یک ربات هوش مصنوعی هستم که در مورد بورسیه‌های دانشجویی و زندگی در شهر پروجا ایتالیا به شما کمک می‌کنم.\n"
            "می‌توانید با استفاده از دکمه‌های منو اطلاعات مورد نظرتان را پیدا کنید، یا سوال خود را به صورت متنی مطرح کنید تا من با هوش مصنوعی پاسخ دهم.",
            reply_markup=get_main_keyboard_markup(context.user_data['current_json_path'])
        )
    return MAIN_MENU

async def handle_free_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_message = update.message.text
    logger.info(f"Free text message from user: {user_message}")
    user_id = update.effective_user.id

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "user", "content": user_message})

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        ai_response = response.choices[0].message.content
        logger.info(f"AI response: {ai_response}")

        first_name = context.user_data.get('first_name')
        age = context.user_data.get('age')
        if first_name and age:
            final_response = f"{first_name} عزیز ({age} ساله)، این پاسخ برای شماست:\n\n{ai_response}"
        elif first_name:
            final_response = f"{first_name} عزیز، این پاسخ برای شماست:\n\n{ai_response}"
        else:
            final_response = ai_response

        await update.message.reply_text(final_response, reply_markup=get_main_keyboard_markup(context.user_data['current_json_path']))
        await append_qa_to_sheet(user_id, user_message, ai_response)

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        await update.message.reply_text(
            "متاسفم، در حال حاضر قادر به پاسخگویی نیستم. لطفاً کمی بعدتر دوباره امتحان کنید.",
            reply_markup=get_main_keyboard_markup(context.user_data['current_json_path'])
        )
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "من فقط در مورد بورسیه‌های دانشجویی و زندگی در شهر پروجا می‌تونم کمکت کنم. سوالاتت رو در این مورد بپرس.",
        reply_markup=get_main_keyboard_markup(context.user_data.get('current_json_path', []))
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "مکالمه لغو شد. هر وقت نیاز داشتی دوباره می‌تونی شروع کنی.",
        reply_markup=get_main_keyboard_markup([])
    )
    return ConversationHandler.END

# --- Initialize Application ---
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# --- Conversation Handler ---
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASKING_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_first_name)],
        ASKING_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_last_name)],
        ASKING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
        ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
        MAIN_MENU: [
            CallbackQueryHandler(handle_json_menu_callback, pattern=r"^json_menu:.*"),
            CallbackQueryHandler(handle_action_callback, pattern=r"^action:.*"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text_message)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(conv_handler)
application.add_handler(CommandHandler("help", help_command))

# --- AsyncIO Event Loop Setup ---
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# --- HTTP Handler for Render ---
@http
def main(request: Request):
    if request.method == "POST" and request.path == f"/{TELEGRAM_BOT_TOKEN}":
        update = Update.de_json(request.get_json(), application.bot)
        # Use run_coroutine_threadsafe to run async function in a separate thread
        future = asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
        future.result()  # Wait for the coroutine to complete
        return "", 200
    return "Invalid request", 400

# --- Initialize Webhook ---
async def set_webhook():
    webhook_url = f"{BASE_URL}/{TELEGRAM_BOT_TOKEN}"
    logger.info(f"Setting webhook to: {webhook_url}")
    try:
        await application.bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET
        )
        logger.info("Webhook set successfully.")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

# --- Run Event Loop in a Separate Thread ---
def run_loop():
    loop.run_forever()

if __name__ == "__main__":
    # Start the event loop in a separate thread
    threading.Thread(target=run_loop, daemon=True).start()
    # Set webhook
    future = asyncio.run_coroutine_threadsafe(set_webhook(), loop)
    future.result()
