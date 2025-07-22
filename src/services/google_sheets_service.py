import logging
from typing import Optional, List
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import logger, GOOGLE_CREDS, SHEET_ID, SCHOLARSHIPS_SHEET_NAME, QUESTIONS_SHEET_NAME

# تنظیمات Google Sheets
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_gspread_client() -> gspread.Client:
    """ایجاد کلاینت Google Sheets."""
    try:
        if not GOOGLE_CREDS:
            logger.error("Google credentials not configured.")
            raise ValueError("Google credentials are missing.")
        # تبدیل رشته JSON به دیکشنری
        import json
        try:
            creds_dict = json.loads(GOOGLE_CREDS)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid GOOGLE_CREDS format: {e}")
            raise ValueError("GOOGLE_CREDS is not a valid JSON string.")
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(credentials)
        logger.info("Google Sheets client initialized successfully.")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets client: {e}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def append_qa_to_sheet(user_id: int, question: str, answer: str) -> None:
    """ذخیره پرس‌وجو و پاسخ در Google Sheet."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID).worksheet(QUESTIONS_SHEET_NAME)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [str(user_id), timestamp, question, answer]
        
        sheet.append_row(row, value_input_option='RAW')
        logger.info(f"Successfully appended Q&A for user {user_id} to sheet '{QUESTIONS_SHEET_NAME}'.")
    except Exception as e:
        logger.error(f"Error appending Q&A for user {user_id}: {e}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_user_history_from_sheet(user_id: int, lang: str = 'fa') -> str:
    """بازیابی تاریخچه پرس‌وجوهای کاربر از Google Sheet."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID).worksheet(QUESTIONS_SHEET_NAME)
        
        records = sheet.get_all_records()
        user_records = [r for r in records if str(r.get('user_id')) == str(user_id)]
        
        if not user_records:
            logger.info(f"No history found for user {user_id}.")
            return "No history found."
        
        history_text_map = {
            'fa': "📜 *تاریخچه پرس‌وجوهای شما*:\n\n",
            'en': "📜 *Your Query History*:\n\n",
            'it': "📜 *Cronologia delle tue domande*:\n\n"
        }
        history_text = history_text_map.get(lang, history_text_map['en'])
        
        for idx, record in enumerate(user_records, 1):
            question = record.get('question', '')
            answer = record.get('answer', '')
            timestamp = record.get('timestamp', 'N/A')
            history_text += (
                f"{idx}. *{timestamp}*\n"
                f"سوال: {question}\n"
                f"پاسخ: {answer}\n\n" if lang == 'fa' else
                f"{idx}. *{timestamp}*\n"
                f"Question: {question}\n"
                f"Answer: {answer}\n\n" if lang == 'en' else
                f"{idx}. *{timestamp}*\n"
                f"Domanda: {question}\n"
                f"Risposta: {answer}\n\n"
            )
        
        logger.info(f"Retrieved history for user {user_id} with {len(user_records)} records.")
        return history_text
    except Exception as e:
        logger.error(f"Error retrieving history for user {user_id}: {e}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_scholarships_from_sheet(lang: str = 'fa') -> List[dict]:
    """بازیابی اطلاعات بورسیه‌ها از Google Sheet."""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID).worksheet(SCHOLARSHIPS_SHEET_NAME)
        
        records = sheet.get_all_records()
        scholarships = []
        
        for record in records:
            scholarship = {
                'title': record.get('title_' + lang, record.get('title_en', 'No Title')),
                'description': record.get('description_' + lang, record.get('description_en', '')),
                'deadline': record.get('deadline', 'N/A'),
                'link': record.get('link', '')
            }
            scholarships.append(scholarship)
        
        logger.info(f"Retrieved {len(scholarships)} scholarships from sheet '{SCHOLARSHIPS_SHEET_NAME}'.")
        return scholarships
    except Exception as e:
        logger.error(f"Error retrieving scholarships: {e}")
        raise
