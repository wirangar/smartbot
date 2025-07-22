import logging
import json
import os
from pathlib import Path
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from src.config import logger, TELEGRAM_BOT_TOKEN, BASE_URL, PORT, WEBHOOK_SECRET
from src.handlers.user_manager import (
    start,
    select_language,
    ask_first_name,
    ask_last_name,
    ask_age,
    ask_email,
    cancel,
    show_profile_command,
    SELECTING_LANG,
    ASKING_FIRST_NAME,
    ASKING_LAST_NAME,
    ASKING_AGE,
    ASKING_EMAIL,
    MAIN_MENU,
)
from src.handlers.menu_handler import main_menu_command, help_command, handle_menu_callback, handle_action_callback
from src.handlers.message_handler import handle_text_message, handle_voice_message
from src.database import initialize_connections, get_db_cursor, get_redis_client
from src.services.isee_service import ISEEService
from src.services.search_engine import SearchEngine
from src.utils.paginator import Paginator
from src.utils.text_formatter import sanitize_markdown
from src.utils.keyboard_builder import get_main_menu_keyboard
from src.data.knowledge_base import get_knowledge_base

async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت دکمه‌های صفحه‌بندی."""
    from src.handlers.user_manager import MAIN_MENU
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get('language', 'fa')
    paginator = Paginator()

    action = query.data.replace("pagination:", "")
    if action == "next":
        page_data = paginator.get_next_page(user_id)
    elif action == "prev":
        page_data = paginator.get_prev_page(user_id)
    else:
        logger.warning(f"Invalid pagination action for user {user_id}: {action}")
        return MAIN_MENU

    if not page_data or 'content' not in page_data:
        messages = {
            'fa': "❌ خطایی در صفحه‌بندی رخ داد یا دیگر صفحه‌ای وجود ندارد.",
            'en': "❌ An error occurred in pagination or no more pages available.",
            'it': "❌ Si è verificato un errore nella paginazione o non ci sono altre pagine."
        }
        await query.message.edit_text(
            sanitize_markdown(messages[lang]),
            parse_mode='MarkdownV2',
            reply_markup=get_main_menu_keyboard(lang)
        )
        return MAIN_MENU

    try:
        await query.message.edit_text(
            sanitize_markdown(
                f"{page_data['content']['content']}\n\n"
                f"{'صفحه' if lang == 'fa' else 'Page' if lang == 'en' else 'Pagina'} "
                f"{page_data['page_num']} {'از' if lang == 'fa' else 'of' if lang == 'en' else 'di'} "
                f"{page_data['total_pages']}"
            ),
            parse_mode='MarkdownV2',
            reply_markup=paginator.get_pagination_markup(page_data, lang)
        )
        if page_data['content']['file_path']:
            try:
                with open(page_data['content']['file_path'], 'rb') as f:
                    if page_data['content']['file_path'].endswith(('.jpg', '.jpeg', '.png')):
                        await query.message.reply_photo(photo=f)
                    elif page_data['content']['file_path'].endswith('.pdf'):
                        await query.message.reply_document(document=f)
            except Exception as e:
                logger.error(f"Error sending file {page_data['content']['file_path']} for user {user_id}: {e}")
    except Exception as e:
        logger.error(f"Error updating pagination message for user {user_id}: {e}")
        messages = {
            'fa': "❌ خطایی در نمایش صفحه رخ داد.",
            'en': "❌ An error occurred while displaying the page.",
            'it': "❌ Si è verificato un errore durante la visualizzazione della pagina."
        }
        await query.message.edit_text(
            sanitize_markdown(messages[lang]),
            parse_mode='MarkdownV2',
            reply_markup=get_main_menu_keyboard(lang)
        )
    return MAIN_MENU

async def main():
    """راه‌اندازی ربات تلگرام با webhook."""
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is not configured.")
        raise ValueError("TELEGRAM_BOT_TOKEN is missing.")

    # بررسی متغیرهای محیطی
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY",
        "DATABASE_URL",
        "GOOGLE_CREDS",
        "SHEET_ID",
        "OPENWEATHERMAP_API_KEY",
        "ADMIN_CHAT_ID",
        "REDIS_URL",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.critical(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")

    # مقداردهی اولیه اتصال‌های پایگاه داده و Redis
    try:
        initialize_connections()
        redis_client = get_redis_client()
        if redis_client is None:
            logger.warning("Redis client not initialized. Pagination and session features may not work.")
    except Exception as e:
        logger.critical(f"Failed to initialize database and Redis connections: {e}")
        raise

    # بارگذاری knowledge base
    try:
        knowledge_base = get_knowledge_base()
        if not knowledge_base:
            logger.error("Knowledge base is empty or failed to load.")
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}")
        knowledge_base = {}

    # ایجاد اپلیکیشن تلگرام
    try:
        application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .read_timeout(10)
            .write_timeout(10)
            .build()
        )
    except Exception as e:
        logger.critical(f"Failed to initialize Telegram application: {e}")
        raise

    # ذخیره knowledge base و db_manager در bot_data
    application.bot_data['knowledge_base'] = knowledge_base
    application.bot_data['db_manager'] = None  # در صورت نیاز به شیء خاص جایگزین شود
    application.bot_data['OPENWEATHERMAP_API_KEY'] = os.getenv("OPENWEATHERMAP_API_KEY")

    # تنظیم ConversationHandler برای ثبت‌نام کاربر، ISEE، و جستجو
    isee_service = ISEEService(knowledge_base, None)
    search_engine = SearchEngine(Paginator())

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", main_menu_command),
            CommandHandler("help", help_command),
            CommandHandler("profile", show_profile_command),
            isee_service.get_conversation_handler().entry_points[0],
        ],
        states={
            SELECTING_LANG: [CallbackQueryHandler(select_language, pattern="^lang:")],
            ASKING_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_first_name)],
            ASKING_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_last_name)],
            ASKING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASKING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            MAIN_MENU: [
                CommandHandler("menu", main_menu_command),
                CommandHandler("help", help_command),
                CommandHandler("profile", show_profile_command),
                CallbackQueryHandler(handle_menu_callback, pattern="^menu:"),
                CallbackQueryHandler(handle_action_callback, pattern="^action:"),
                CallbackQueryHandler(handle_pagination, pattern="^pagination:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message),
                MessageHandler(filters.VOICE, handle_voice_message),
                search_engine.get_handler(),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # اضافه کردن ConversationHandler به اپلیکیشن
    application.add_handler(conv_handler)

    # مدیریت خطاها
    async def error_handler(update, context):
        logger.error(f"Update {update} caused error: {context.error}")
        if update and update.effective_message:
            error_text = {
                'fa': "خطایی رخ داد. لطفاً دوباره امتحان کنید.",
                'en': "An error occurred. Please try again.",
                'it': "Si è verificato un errore. Riprova."
            }
            lang = context.user_data.get('language', 'fa') if context.user_data else 'fa'
            await update.effective_message.reply_text(
                sanitize_markdown(error_text.get(lang)),
                parse_mode='MarkdownV2',
            )

    application.add_error_handler(error_handler)

    # راه‌اندازی webhook
    webhook_url = f"{BASE_URL}/webhook"
    try:
        await application.initialize()
        await application.bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=["message", "callback_query"],
        )
        logger.info(f"Webhook set successfully at {webhook_url}")

        await application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            secret_token=WEBHOOK_SECRET,
            webhook_url=webhook_url,
        )
    except Exception as e:
        logger.critical(f"Failed to start webhook: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
