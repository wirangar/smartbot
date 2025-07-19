import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import logging
import os
from datetime import datetime
from config import (
    GOOGLE_CREDS,
    SHEET_ID,
    SCHOLARSHIPS_SHEET_NAME,
    BAZARINO_ORDERS_SHEET_NAME,
)

logger = logging.getLogger(__name__)

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

        if scholarships_sheet or bazarino_orders_sheet:
            logger.info("Google Sheets initialized successfully.")
        else:
            logger.warning("No worksheets could be initialized.")
    except json.JSONDecodeError:
        logger.error("Error decoding GOOGLE_CREDS_JSON. Make sure it's a valid JSON string.")
    except Exception as e:
        logger.error(f"Error initializing Google Sheets: {str(e)}")
        gc = None
        scholarships_sheet = None
        bazarino_orders_sheet = None

async def append_user_data_to_sheet(user_data: dict) -> bool:
    if not scholarships_sheet:
        logger.warning("Google Sheet (Scholarship) not initialized. Cannot append user data.")
        return False
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
        logger.info(f"User data appended to Google Sheet: {user_data['telegram_id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to append user data to Google Sheet: {e}")
        return False

async def append_qa_to_sheet(telegram_id: int, question: str, answer: str) -> bool:
    if not bazarino_orders_sheet:
        logger.warning("Google Sheet (Bazarino Orders) not initialized. Cannot append Q&A.")
        return False
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [telegram_id, question, answer, timestamp]
        bazarino_orders_sheet.append_row(row)
        logger.info(f"Q&A appended to Google Sheet for user {telegram_id}.")
        return True
    except Exception as e:
        logger.error(f"Failed to append Q&A to Google Sheet: {e}")
        return False

async def get_previous_answers(telegram_id: int) -> str:
    if not bazarino_orders_sheet:
        return "قابلیت نمایش پاسخ‌های قبلی در دسترس نیست."
    try:
        records = bazarino_orders_sheet.get_all_records()
        user_answers = [
            f"سوال: {record['question']}\nپاسخ: {record['answer']}\nزمان: {record['timestamp']}"
            for record in records if str(record.get('telegram_id')) == str(telegram_id)
        ]
        if user_answers:
            return "\n\n".join(user_answers)
        else:
            return "هیچ سوال و پاسخی برای شما ثبت نشده است."
    except Exception as e:
        logger.error(f"Error fetching previous answers: {e}")
        return "خطایی در دریافت پاسخ‌های قبلی رخ داد."

# Initialize sheets on module load
init_google_sheets()
