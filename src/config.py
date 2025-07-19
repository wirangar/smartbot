import os
import logging

# --- Telegram Bot Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
BASE_URL = os.getenv("BASE_URL")
PORT = int(os.getenv("PORT", 8080))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Database Configuration ---
# PostgreSQL for persistent data
DATABASE_URL = os.getenv("DATABASE_URL")
# Redis for temporary session data
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# --- Google Sheets Configuration ---
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS") # Path to credentials file for Render
SHEET_ID = os.getenv("SHEET_ID")
SCHOLARSHIPS_SHEET_NAME = os.getenv("SPREADSHEET_NAME", "Scholarship")
QUESTIONS_SHEET_NAME = os.getenv("QUESTIONS_SHEET_NAME", "Bazarino Orders")

# --- System Prompts & Messages ---
SYSTEM_PROMPT = """
You are Scholarino, an intelligent assistant for students in Perugia, Italy.
Your goal is to provide accurate and friendly information based on the knowledge base provided.
Always respond in the user's chosen language (fa/en/it).
If a question is outside your scope (student life in Perugia), politely state that you cannot answer.
"""

# --- Logging Setup ---
def setup_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    logger.info("--- Scholarino Bot Logging Initialized ---")
    # Log critical environment variables for debugging
    for var in ["TELEGRAM_TOKEN", "OPENAI_API_KEY", "DATABASE_URL", "REDIS_URL", "ADMIN_CHAT_ID"]:
        logger.info(f"{var}: {'Set' if os.getenv(var) else 'Not set'}")
    return logger

logger = setup_logging()
