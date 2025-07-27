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
class MissingEnvVarError(Exception):
    pass

def validate_env_vars():
    """بررسی وجود متغیرهای محیطی موردنیاز."""
    required_vars = [
        "TELEGRAM_TOKEN",
        "OPENAI_API_KEY",
        "DATABASE_URL",
        "GOOGLE_CREDS",
        "SHEET_ID",
        "OPENWEATHERMAP_API_KEY",
        "ADMIN_CHAT_ID"
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        message = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.critical(message)
        raise ValueError(message)

# متغیرهای محیطی
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")  # اختیاری، اگر استفاده نشود خطا نمی‌دهد
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")
SHEET_ID = os.getenv("SHEET_ID")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
SCHOLARSHIPS_SHEET_NAME = os.getenv("SCHOLARSHIPS_SHEET_NAME", "Scholarships")
QUESTIONS_SHEET_NAME = os.getenv("QUESTIONS_SHEET_NAME", "UserQuestions")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "scholarino-secret")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# OpenAI models
OPENAI_CHAT_MODEL = "gpt-4o"
OPENAI_WHISPER_MODEL = "whisper-1"

# OpenAI models
OPENAI_CHAT_MODEL = "gpt-4o"
OPENAI_WHISPER_MODEL = "whisper-1"

# Paginator settings
PAGINATION_EXPIRE_TIME = 3600  # 1 hour

# ISEE calculation parameters
ISEE_FAMILY_PARAMS = {1: 1.00, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85}
ISEE_PROPERTY_VALUE_MULTIPLIER = 500
ISEE_PROPERTY_VALUE_PERCENTAGE = 0.2
ISEE_FULL_SCHOLARSHIP_THRESHOLD_MULTIPLIER = 0.55
ISEE_MEDIUM_SCHOLARSHIP_THRESHOLD_MULTIPLIER = 0.715
ISEE_FULL_SCHOLARSHIP_AMOUNT = 5192
ISEE_MEDIUM_SCHOLARSHIP_AMOUNT = 3634
ISEE_PARTIAL_SCHOLARSHIP_AMOUNT = 2000

# بررسی متغیرهای محیطی
validate_env_vars()
