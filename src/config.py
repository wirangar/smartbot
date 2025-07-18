import os
import logging

# --- Load Environment Variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 8080))
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")  # Changed to accept JSON content directly
SHEET_ID = os.getenv("SHEET_ID")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))
SCHOLARSHIPS_SHEET_NAME = "Scholarship"
BAZARINO_ORDERS_SHEET_NAME = "Bazarino Orders"

# --- System Prompt ---
SYSTEM_PROMPT = """
تو یک ربات هوش مصنوعی هستی که فقط در مورد بورسیه‌های دانشجویی و زندگی دانشجویی در شهر پروجا، ایتالیا اطلاعات ارائه می‌دهی.
پاسخ‌هایت را به زبان فارسی بده.
اگر اطلاعات مشخص و دقیقی در مورد سوال کاربر در دانش داخلی‌ات یا متنی که به تو داده می‌شود وجود دارد، از همان اطلاعات استفاده کن و به هیچ عنوان از آن منحرف نشو.
اگر سوالی خارج از این موضوع (بورسیه‌های دانشجویی و زندگی در پروجا) از تو پرسیده شد، مودبانه و به فارسی بگو که فقط در مورد بورسیه‌های دانشجویی و زندگی در پروجا می‌توانی کمک کنی و نمی‌توانی به سوالات دیگر پاسخ دهی.
اطلاعاتی که می‌دهی باید بر اساس داده‌های عمومی و موجود در مورد بورسیه‌های پروجا و زندگی دانشجویی باشد.
مهم: هرگز خارج از حوزه بورسیه‌های دانشجویی و زندگی در پروجا پاسخ نده.
"""

# --- Logging Setup ---
def setup_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    logger.info("Logging configured.")
    # Log environment variable status for debugging
    logger.info(f"TELEGRAM_TOKEN: {'Set' if TELEGRAM_BOT_TOKEN else 'Not set'}")
    logger.info(f"OPENAI_API_KEY: {'Set' if OPENAI_API_KEY else 'Not set'}")
    logger.info(f"WEBHOOK_SECRET: {'Set' if WEBHOOK_SECRET else 'Not set'}")
    logger.info(f"BASE_URL: {BASE_URL}")
    logger.info(f"PORT: {PORT}")
    logger.info(f"GOOGLE_CREDS_JSON: {'Set' if GOOGLE_CREDS_JSON else 'Not set'}")
    logger.info(f"SHEET_ID: {SHEET_ID}")
    logger.info(f"ADMIN_CHAT_ID: {ADMIN_CHAT_ID}")
    return logger

logger = setup_logging()
