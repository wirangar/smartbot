import logging
from telegram.ext import (
 Application,
 CommandHandler,
 MessageHandler,
 CallbackQueryHandler,
 ConversationHandler,
 filters
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
 SELECTING_LANG, ASKING_FIRST_NAME, ASKING_LAST_NAME, ASKING_AGE, ASKING_EMAIL, MAIN_MENU
)
from src.handlers.menu_handler import main_menu_command, help_command, handle_menu_callback, handle_action_callback
from src.handlers.message_handler import handle_text_message, handle_voice_message
from src.database import initialize_connections

async def main():
 """راه‌اندازی ربات تلگرام با webhook."""
 if not TELEGRAM_BOT_TOKEN:
 logger.critical("TELEGRAM_BOT_TOKEN is not configured.")
 raise ValueError("TELEGRAM_BOT_TOKEN is missing.")

 # مقداردهی اولیه اتصال‌های پایگاه داده و Redis
 try:
 initialize_connections()
 except Exception as e:
 logger.critical(f"Failed to initialize database and Redis connections: {e}")
 raise

 # ایجاد اپلیکیشن تلگرام
 application = (
 Application.builder()
 .token(TELEGRAM_BOT_TOKEN)
 .read_timeout(10)
 .write_timeout(10)
 .build()
 )

 # تنظیم ConversationHandler برای ثبت‌نام کاربر
 conv_handler = ConversationHandler(
 entry_points=[CommandHandler("start", start)],
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
 MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message),
 MessageHandler(filters.VOICE, handle_voice_message),
 ],
 },
 fallbacks=[CommandHandler("cancel", cancel)],
 )

 # اضافه کردن ConversationHandler به اپلیکیشن
 application.add_handler(conv_handler)

 # مدیریت خطاها
 async def error_handler(update, context):
 logger.error(f"Update { update} caused error: {context.error}")
 if update and update.effective_message:
 error_text = {
 'fa': "خطایی رخ داد. لطفاً دوباره امتحان کنید.",
 'en': "An error occurred. Please try again.",
 'it': "Si è verificato un errore. Riprova."
 }
 lang = context.user_data.get('language', 'fa') if context.user_data else 'fa'
 await update.effective_message.reply_text(error_text.get(lang))

 application.add_error_handler(error_handler)

 # راه‌اندازی webhook
 webhook_url = f"{BASE_URL}/webhook"
 try:
 await application.initialize()
 await application.bot.set_webhook(
 url=webhook_url,
 secret_token=WEBHOOK_SECRET,
 allowed_updates=["message", "callback_query"]
 )
 logger.info(f"Webhook set successfully at {webhook_url}")

 # راه‌اندازی سرور webhook
 await application.run_webhook(
 listen="0.0.0.0",
 port=PORT,
 secret_token=WEBHOOK_SECRET,
 webhook_url=webhook_url
 )
 except Exception as e:
 logger.critical(f"Failed to start webhook: {e}")
 raise

if __name__ == "__main__":
 import asyncio
 asyncio.run(main())
