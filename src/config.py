import os
import logging
from pathlib import Path

# تنظیم لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# مسیر پایه پروژه
BASE_DIR = Path(__file__).parent.parent

# متغیرهای محیطی
def validate_env_vars():
    """بررسی وجود متغیرهای محیطی موردنیاز."""
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

# متغیرهای محیطی
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")
SHEET_ID = os.getenv("SHEET_ID")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
SCHOLARSHIPS_SHEET_NAME = os.getenv("SCHOLARSHIPS_SHEET_NAME", "Scholarship")
QUESTIONS_SHEET_NAME = os.getenv("QUESTIONS_SHEET_NAME", "Bazarino Orders")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "scholarino-secret")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# بررسی متغیرهای محیطی
validate_env_vars()
