



import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ConversationHandler
)
from utils.google_sheets import GoogleSheetsClient
from utils.response_builder import ResponseBuilder
from utils.language_switcher import LanguageSwitcher
import os
from datetime import datetime
from fuzzywuzzy import fuzz

# Load configuration from environment variables
config = {
    "google_sheets": {
        "sheet_id": os.getenv("SHEET_ID"),
        "credentials_file": os.getenv("GOOGLE_CREDS", "service_account.json"),
        "worksheet_name": os.getenv("SPREADSHEET_NAME", "Scholarship"),
        "questions_worksheet": os.getenv("QUESTIONS_SHEET_NAME", "Bazarino Orders")
    },
    "telegram": {
        "token": os.getenv("TELEGRAM_TOKEN")
    },
    "webhook": {
        "enabled": True,
        "port": int(os.getenv("PORT", 8080)),
        "url": os.getenv("BASE_URL", "https://your-app-name.onrender.com")
    }
}
print(f"🔍 Sheet ID is: {config['google_sheets']['sheet_id']}")

# Initialize clients
sheets_client = GoogleSheetsClient(config['google_sheets'])
response_builder = ResponseBuilder('data/knowledge.json')
language_switcher = LanguageSwitcher('lang')

# States for conversation handler
NAME, LAST_NAME, AGE, EMAIL = range(4)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    lang = language_switcher.get_user_language(user.id)
    
    # Check if user exists in sheet
    user_data = sheets_client.get_user_data(user.id)
    
    if not user_data:
        # New user - ask for registration
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=language_switcher.get_translation(lang, 'welcome_new_user').format(name=user.first_name),
            reply_markup=main_menu_keyboard(lang)
        )
        return NAME
    else:
        # Existing user
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=language_switcher.get_translation(lang, 'welcome_back').format(name=user_data['first_name']),
            reply_markup=main_menu_keyboard(lang)
        )
        return ConversationHandler.END

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = language_switcher.get_user_language(update.effective_user.id)
    await update.message.reply_text(language_switcher.get_translation(lang, 'ask_name'))
    return NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    lang = language_switcher.get_user_language(update.effective_user.id)
    await update.message.reply_text(language_switcher.get_translation(lang, 'ask_last_name'))
    return LAST_NAME

async def receive_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['last_name'] = update.message.text
    lang = language_switcher.get_user_language(update.effective_user.id)
    await update.message.reply_text(language_switcher.get_translation(lang, 'ask_age'))
    return AGE

async def receive_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['age'] = update.message.text
    lang = language_switcher.get_user_language(update.effective_user.id)
    await update.message.reply_text(language_switcher.get_translation(lang, 'ask_email'))
    return EMAIL

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['email'] = update.message.text
    user = update.effective_user
    lang = language_switcher.get_user_language(user.id)
    
    # Save user data
    user_data = {
        'telegram_id': user.id,
        'first_name': context.user_data['name'],
        'last_name': context.user_data['last_name'],
        'age': context.user_data['age'],
        'email': context.user_data['email'],
        'language': lang,
        'registration_date': datetime.now().isoformat()
    }
    
    sheets_client.save_user_data(user_data)
    
    await update.message.reply_text(
        language_switcher.get_translation(lang, 'registration_complete'),
        reply_markup=main_menu_keyboard(lang)
    )
    return ConversationHandler.END

def main_menu_keyboard(lang):
    keyboard = [
        [InlineKeyboardButton(language_switcher.get_translation(lang, 'menu_new_question'), callback_data='new_question')],
        [InlineKeyboardButton(language_switcher.get_translation(lang, 'menu_previous_answers'), callback_data='previous_answers')],
        [InlineKeyboardButton(language_switcher.get_translation(lang, 'menu_help'), callback_data='help')],
        [InlineKeyboardButton(language_switcher.get_translation(lang, 'menu_change_language'), callback_data='change_language')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    lang = language_switcher.get_user_language(user.id)
    user_data = sheets_client.get_user_data(user.id)
    
    if query.data == 'new_question':
        await query.edit_message_text(language_switcher.get_translation(lang, 'ask_question'))
    elif query.data == 'previous_answers':
        # Get previous answers from sheet
        answers = sheets_client.get_user_questions(user.id)
        if answers:
            response = language_switcher.get_translation(lang, 'previous_answers_header') + "\n\n"
            for answer in answers:
                response += f"📌 {answer['question']}\n🔹 {answer['answer']}\n\n"
            await query.edit_message_text(response)
        else:
            await query.edit_message_text(language_switcher.get_translation(lang, 'no_previous_answers'))
    elif query.data == 'help':
        await query.edit_message_text(language_switcher.get_translation(lang, 'help_message'))
    elif query.data == 'change_language':
        keyboard = [
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data='set_lang_fa')],
            [InlineKeyboardButton("🇮🇹 Italiano", callback_data='set_lang_it')],
            [InlineKeyboardButton("🇬🇧 English", callback_data='set_lang_en')]
        ]
        await query.edit_message_text(
            language_switcher.get_translation(lang, 'choose_language'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    lang = query.data.split('_')[-1]  # fa, it, en
    user = update.effective_user
    
    language_switcher.set_user_language(user.id, lang)
    sheets_client.update_user_language(user.id, lang)
    
    await query.edit_message_text(
        language_switcher.get_translation(lang, 'language_set'),
        reply_markup=main_menu_keyboard(lang)
    )

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = language_switcher.get_user_language(user.id)
    user_data = sheets_client.get_user_data(user.id)
    
    question = update.message.text
    
    # Send searching message
    searching_msg = await update.message.reply_text(language_switcher.get_translation(lang, 'searching_answer'))
    
    # Get response from knowledge base
    response = response_builder.get_response(question, lang)
    
    # Format personalized response
    personalized_response = language_switcher.get_translation(lang, 'personalized_response').format(
        name=user_data['first_name'],
        response=response
    )
    
    # Save question and answer to sheet
    sheets_client.save_question_answer(
        user.id,
        question,
        response,
        datetime.now().isoformat()
    )
    
    # Edit the searching message with the actual response
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=searching_msg.message_id,
        text=personalized_response,
        reply_markup=main_menu_keyboard(lang)
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and send a message to the user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    if update.effective_user:
        lang = language_switcher.get_user_language(update.effective_user.id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=language_switcher.get_translation(lang, 'error_occurred')
        )

def main():
    # Create the Application
    application = ApplicationBuilder().token(config['telegram']['token']).build()
    
    # Add conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_last_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_age)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_menu, pattern='^(new_question|previous_answers|help|change_language)$'))
    application.add_handler(CallbackQueryHandler(set_language, pattern='^set_lang_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))
    application.add_error_handler(error_handler)
    
    # Run the bot
    if config.get('webhook', {}).get('enabled', False):
        application.run_webhook(
            listen="0.0.0.0",
            port=config['webhook']['port'],
            url_path=config['telegram']['token'],
            webhook_url=f"{config['webhook']['url']}/{config['telegram']['token']}"
        )
    else:
        application.run_polling()

if __name__ == '__main__':
    main()
