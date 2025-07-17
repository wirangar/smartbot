import logging
import os
import json
import gspread # For Google Sheets
from oauth2client.service_account import ServiceAccountCredentials # For Google Sheets Auth
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
import tempfile # For handling Google credentials securely
from datetime import datetime # Added for timestamp

# --- Load Environment Variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 8080))

# Google Sheets specific environment variables
GOOGLE_CREDENTIALS_JSON_CONTENT = os.getenv("GOOGLE_CREDENTIALS_JSON_CONTENT")
SHEET_ID = os.getenv("SHEET_ID")
# SPREADSHEET_NAME is not directly used by gspread.open_by_key, but for clarity
# SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
SCHOLARSHIPS_SHEET_NAME = "scholarships" # As per user's info
BAZARINO_ORDERS_SHEET_NAME = "Bazarino Orders" # As per user's info

# --- Set up Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Initialize OpenAI client ---
openai.api_key = OPENAI_API_KEY

# --- Google Sheets Setup ---
gc = None # Global variable for gspread client
scholarships_sheet = None
bazarino_orders_sheet = None # New: for storing Q&A

def init_google_sheets():
    global gc, scholarships_sheet, bazarino_orders_sheet
    try:
        # Create a temporary file for credentials
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_creds_file:
            temp_creds_file.write(GOOGLE_CREDENTIALS_JSON_CONTENT)
            creds_path = temp_creds_file.name
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        gc = gspread.authorize(creds)
        
        # Open the specific spreadsheet
        spreadsheet = gc.open_by_key(SHEET_ID)
        
        # Get individual sheets
        scholarships_sheet = spreadsheet.worksheet(SCHOLARSHIPS_SHEET_NAME)
        bazarino_orders_sheet = spreadsheet.worksheet(BAZARINO_ORDERS_SHEET_NAME) # Initialize Bazarino Orders sheet
        
        logger.info("Google Sheets initialized successfully.")
        
        # Clean up temporary file
        os.remove(creds_path)
    except Exception as e:
        logger.error(f"Error initializing Google Sheets: {e}")
        # If Google Sheets fails, the bot should still function for AI/JSON
        gc = None
        scholarships_sheet = None
        bazarino_orders_sheet = None

# Call this function once when the bot starts
init_google_sheets()

async def append_user_data_to_sheet(user_data: dict) -> bool:
    """Appends user registration data to the 'scholarships' Google Sheet."""
    if scholarships_sheet:
        try:
            # Headers from user's info: telegram_id,first_name,last_name,age,email,language,registration_date
            row = [
                user_data.get('telegram_id', ''),
                user_data.get('first_name', ''),
                user_data.get('last_name', ''),
                user_data.get('age', ''),
                user_data.get('email', ''),
                user_data.get('language', 'fa'), # Default to Persian
                user_data.get('registration_date', '') # Will be current date
            ]
            scholarships_sheet.append_row(row)
            logger.info(f"User data appended to Google Sheet: {user_data}")
            return True
        except Exception as e:
            logger.error(f"Failed to append user data to Google Sheet: {e}")
            return False
    else:
        logger.warning("Google Sheet (Scholarships) not initialized. Cannot append user data.")
        return False

async def append_qa_to_sheet(telegram_id: int, question: str, answer: str) -> bool:
    """Appends question and answer to the 'Bazarino Orders' Google Sheet."""
    if bazarino_orders_sheet:
        try:
            # Headers from user's info: telegram_id,question,answer,timestamp
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
        logger.error(f"Knowledge base file '{KNOWLEDGE_FILE}' not found. AI will rely only on its general knowledge.")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from '{KNOWLEDGE_FILE}'. Check file format.")

# Call this function once when the bot starts
load_knowledge_base()

# --- Conversation States for User Info Collection ---
ASKING_FIRST_NAME, ASKING_LAST_NAME, ASKING_AGE, ASKING_EMAIL, MAIN_MENU = range(5)

# --- Define the system prompt for your AI ---
SYSTEM_PROMPT = """
تو یک ربات هوش مصنوعی هستی که فقط در مورد بورسیه‌های دانشجویی و زندگی دانشجویی در شهر پروجا، ایتالیا اطلاعات ارائه می‌دهی.
پاسخ‌هایت را به زبان فارسی بده.
اگر اطلاعات مشخص و دقیقی در مورد سوال کاربر در دانش داخلی‌ات یا متنی که به تو داده می‌شود وجود دارد، از همان اطلاعات استفاده کن و به هیچ عنوان از آن منحرف نشو.
اگر سوالی خارج از این موضوع (بورسیه‌های دانشجویی و زندگی در پروجا) از تو پرسیده شد، مودبانه و به فارسی بگو که فقط در مورد بورسیه‌های دانشجویی و زندگی در پروجا می‌توانی کمک کنی و نمی‌توانی به سوالات دیگر پاسخ دهی.
اطلاعاتی که می‌دهی باید بر اساس داده‌های عمومی و موجود در مورد بورسیه‌های پروجا و زندگی دانشجویی باشد.
مهم: هرگز خارج از حوزه بورسیه‌های دانشجویی و زندگی در پروجا پاسخ نده.
"""

def get_json_content_by_path(path_parts: list) -> str:
    """Navigates the knowledge_base JSON using a list of path parts and returns the content."""
    current_level = knowledge_base
    content = ""
    try:
        for i, part in enumerate(path_parts):
            if isinstance(current_level, dict):
                # Find the category or item by its 'title' or 'fa.title'
                found_item = None
                if i == 0: # First part is a category name
                    current_level = current_level.get(part)
                    if not current_level: return "" # Category not found
                    continue
                else: # Subsequent parts are item titles within a category
                    for item in current_level:
                        title = item.get('title')
                        if not title and 'fa' in item and 'title' in item['fa']:
                            title = item['fa']['title']
                        if title == part:
                            found_item = item
                            break
                    if not found_item: return "" # Item not found
                    current_level = found_item

            if i == len(path_parts) - 1: # This is the final item
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
                
                if not content and 'content' in current_level: # Fallback to general content if fa not found
                    content = current_level['content']
                elif not content and 'points' in current_level:
                    content = "\n".join(current_level['points'])
                
        return content
    except Exception as e:
        logger.error(f"Error navigating JSON path {path_parts}: {e}")
        return ""

def get_main_keyboard_markup(current_path_parts: list = None) -> InlineKeyboardMarkup:
    """Generates the main keyboard with JSON categories/items and action buttons."""
    if current_path_parts is None:
        current_path_parts = []

    keyboard = []
    
    # Add JSON navigation buttons
    if not current_path_parts: # At main JSON menu (showing categories)
        for category_name in knowledge_base.keys():
            keyboard.append([InlineKeyboardButton(category_name, callback_data=f"json_menu:{category_name}")])
    else: # Inside a JSON category/item, show sub-items if applicable
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
                if not current_level: break # Path not found

        if isinstance(current_level, list): # Show items within this category/list
            for item in current_level:
                title = item.get('title')
                if not title and 'fa' in item and 'title' in item['fa']:
                    title = item['fa']['title']
                if title:
                    callback_data = ":".join(current_path_parts + [title])
                    keyboard.append([InlineKeyboardButton(title, callback_data=f"json_menu:{callback_data}")])

    # Add "Back" button if not at the main JSON menu
    if current_path_parts:
        back_path = ":".join(current_path_parts[:-1]) if len(current_path_parts) > 1 else "main_menu"
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"json_menu:{back_path}")])
    
    # Add main action buttons
    action_buttons = [
        InlineKeyboardButton("📩 ثبت سوال جدید", callback_data="action:new_question"),
        InlineKeyboardButton("📜 پاسخ‌های قبلی", callback_data="action:previous_answers"),
        InlineKeyboardButton("❓ راهنما", callback_data="action:help")
    ]
    keyboard.append(action_buttons) # Add action buttons in a new row

    return InlineKeyboardMarkup(keyboard)

# --- Handlers for Conversation Flow ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for the first name."""
    user = update.effective_user
    context.user_data['telegram_id'] = user.id
    context.user_data['registration_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context.user_data['current_json_path'] = [] # Initialize JSON path

    welcome_message = (
        f"سلام {user.mention_html()} عزیز! 👋\n"
        "به ربات راهنمای بورسیه و زندگی دانشجویی در پروجا خوش آمدید.\n"
        "من اینجا هستم تا به شما در مسیر تحصیل و اقامت در پروجا کمک کنم.\n\n"
        "برای شروع، لطفاً نام خود را وارد کنید:"
    )
    await update.message.reply_html(welcome_message)
    return ASKING_FIRST_NAME

async def ask_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the first name and asks for the last name."""
    context.user_data['first_name'] = update.message.text
    await update.message.reply_text("حالا لطفاً نام خانوادگی خود را وارد کنید:")
    return ASKING_LAST_NAME

async def ask_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the last name and asks for the age."""
    context.user_data['last_name'] = update.message.text
    await update.message.reply_text("سن خود را به عدد وارد کنید:")
    return ASKING_AGE

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the age and asks for the email."""
    try:
        age = int(update.message.text)
        if not (0 < age < 100): # Basic validation
            await update.message.reply_text("لطفاً یک سن معتبر وارد کنید (بین 1 تا 99 سال).")
            return ASKING_AGE
        context.user_data['age'] = age
        await update.message.reply_text("لطفاً ایمیل خود را وارد کنید:")
        return ASKING_EMAIL
    except ValueError:
        await update.message.reply_text("سن باید یک عدد باشد. لطفاً دوباره وارد کنید:")
        return ASKING_AGE

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the email, saves data to Google Sheet, and transitions to main menu."""
    email = update.message.text
    # Basic email validation (can be more robust)
    if "@" not in email or "." not in email:
        await update.message.reply_text("لطفاً یک ایمیل معتبر وارد کنید.")
    else:
        context.user_data['email'] = email

        # Save data to Google Sheet
        if await append_user_data_to_sheet(context.user_data):
            logger.info("User data successfully saved to Google Sheet.")
        else:
            logger.warning("Could not save user data to Google Sheet.")
        
        # Personalized welcome message
        first_name = context.user_data.get('first_name', 'دوست')
        age = context.user_data.get('age', 'نامشخص')
        personalized_message = (
            f"عالیه، {first_name} عزیز! شما با سن {age} سال، آماده‌اید تا از خدمات ربات استفاده کنید.\n"
            "حالا می‌توانید از منوی زیر برای دسترسی به اطلاعات استفاده کنید یا سوال خود را مطرح کنید:"
        )
        await update.message.reply_text(personalized_message, reply_markup=get_main_keyboard_markup(context.user_data['current_json_path']))
        
        return MAIN_MENU
    return ASKING_EMAIL # If email invalid, stay in this state

async def handle_json_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles callback queries related to JSON menu navigation."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    # Expected format: "json_menu:path_part1:path_part2:..." or "json_menu:main_menu"
    path_indicator = data[1] if len(data) > 1 else ""

    if path_indicator == "main_menu":
        context.user_data['current_json_path'] = []
    else:
        context.user_data['current_json_path'] = data[1:]

    current_path_parts = context.user_data['current_json_path']

    # Check if the last part of the path corresponds to a content item
    content_to_display = ""
    if current_path_parts:
        content_to_display = get_json_content_by_path(current_path_parts)
    
    if content_to_display:
        await query.edit_message_text(content_to_display, reply_markup=get_main_keyboard_markup(current_path_parts))
    else:
        # If no content, it means it's a sub-menu or main category
        message_text = "لطفاً یک گزینه را انتخاب کنید:"
        if not current_path_parts:
            message_text = "لطفاً یک دسته را انتخاب کنید یا سوال خود را مطرح کنید:"
        
        await query.edit_message_text(message_text, reply_markup=get_main_keyboard_markup(current_path_parts))
    
    return MAIN_MENU

async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles callback queries for action buttons."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1] # e.g., "new_question", "previous_answers", "help"

    if action == "new_question":
        context.user_data['current_json_path'] = [] # Reset JSON path
        await query.edit_message_text(
            "لطفاً سوال جدید خود را مطرح کنید. من تلاش می‌کنم با هوش مصنوعی به آن پاسخ دهم.\n"
            "برای بازگشت به منوها می‌توانید دکمه‌های زیر را انتخاب کنید:",
            reply_markup=get_main_keyboard_markup(context.user_data['current_json_path']) # Show main keyboard again
        )
    elif action == "previous_answers":
        # TODO: Implement fetching and displaying previous answers from Bazarino Orders sheet
        await query.edit_message_text(
            "قابلیت نمایش پاسخ‌های قبلی در حال توسعه است و به زودی اضافه خواهد شد. 🙏",
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
    """Processes user messages (free text) and sends them to the AI."""
    user_message = update.message.text
    logger.info(f"Free text message from user: {user_message}")
    
    user_id = update.effective_user.id

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "user", "content": user_message})

    try:
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",  # Or "gpt-3.5-turbo"
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        ai_response = response.choices[0].message.content
        logger.info(f"AI response: {ai_response}")

        # Personalize AI response if user data is available
        first_name = context.user_data.get('first_name')
        age = context.user_data.get('age')
        
        if first_name and age:
            final_response = f"{first_name} عزیز ({age} ساله)، این پاسخ برای شماست:\n\n{ai_response}"
        elif first_name:
            final_response = f"{first_name} عزیز، این پاسخ برای شماست:\n\n{ai_response}"
        else:
            final_response = ai_response

        await update.message.reply_text(final_response, reply_markup=get_main_keyboard_markup(context.user_data['current_json_path']))
        
        # Store Q&A in Google Sheet
        await append_qa_to_sheet(user_id, user_message, ai_response)

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        await update.message.reply_text(
            "متاسفم، در حال حاضر قادر به پاسخگویی نیستم. لطفاً کمی بعدتر دوباره امتحان کنید.",
            reply_markup=get_main_keyboard_markup(context.user_data['current_json_path'])
        )
    return MAIN_MENU # Stay in main menu state

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    await update.message.reply_text(
        "من فقط در مورد بورسیه‌های دانشجویی و زندگی در شهر پروجا می‌تونم کمکت کنم. سوالاتت رو در این مورد بپرس.",
        reply_markup=get_main_keyboard_markup(context.user_data.get('current_json_path', []))
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "مکالمه لغو شد. هر وقت نیاز داشتی دوباره می‌تونی شروع کنی.",
        reply_markup=get_main_keyboard_markup([]) # Show main menu when cancelling
    )
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conversation Handler for user info collection and main menu
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_first_name)],
            ASKING_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_last_name)],
            ASKING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            MAIN_MENU: [
                CallbackQueryHandler(handle_json_menu_callback, pattern=r"^json_menu:.*"), # For JSON menu buttons
                CallbackQueryHandler(handle_action_callback, pattern=r"^action:.*"), # For new action buttons
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text_message) # For free-text questions
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command)) # Add help command outside conversation for flexibility

    # --- Webhook Setup for Render ---
    if BASE_URL and TELEGRAM_BOT_TOKEN and WEBHOOK_SECRET and PORT:
        webhook_url = f"{BASE_URL}/{TELEGRAM_BOT_TOKEN}"
        logger.info(f"Setting webhook to: {webhook_url}")
        
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=webhook_url,
            secret_token=WEBHOOK_SECRET
        )
        logger.info("Bot started with webhook!")
    else:
        logger.warning("Missing environment variables for webhook. Falling back to polling (not recommended for Render).")
        logger.info("Bot started with polling (Ctrl-C to stop).")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
