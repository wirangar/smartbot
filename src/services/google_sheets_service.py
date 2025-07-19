import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import logging
from datetime import datetime

from src.config import (
    GOOGLE_CREDS,
    SHEET_ID,
    SCHOLARSHIPS_SHEET_NAME,
    QUESTIONS_SHEET_NAME,
    logger
)

gc = None
scholarships_sheet = None
questions_sheet = None

def init_google_sheets():
    """Initializes the connection to Google Sheets."""
    global gc, scholarships_sheet, questions_sheet
    try:
        if not GOOGLE_CREDS or not SHEET_ID:
            logger.warning("Google Sheets credentials or Sheet ID are not set. Functionality will be disabled.")
            return

        if not os.path.exists(GOOGLE_CREDS):
            logger.error(f"Credentials file not found at {GOOGLE_CREDS}")
            return

        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS, scope)
        gc = gspread.authorize(creds)

        spreadsheet = gc.open_by_key(SHEET_ID)

        # Initialize Scholarship sheet
        try:
            scholarships_sheet = spreadsheet.worksheet(SCHOLARSHIPS_SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{SCHOLARSHIPS_SHEET_NAME}' not found.")
            scholarships_sheet = None

        # Initialize Questions sheet
        try:
            questions_sheet = spreadsheet.worksheet(QUESTIONS_SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{QUESTIONS_SHEET_NAME}' not found.")
            questions_sheet = None

        if scholarships_sheet or questions_sheet:
            logger.info("Google Sheets initialized successfully.")
        else:
            logger.warning("Could not initialize any Google Sheets worksheets.")

    except Exception as e:
        logger.error(f"Error initializing Google Sheets: {e}")
        gc = None
        scholarships_sheet = None
        questions_sheet = None

async def append_qa_to_sheet(telegram_id: int, question: str, answer: str) -> bool:
    """Appends a question and answer pair to the Google Sheet."""
    if not questions_sheet:
        logger.warning("Questions sheet is not initialized. Cannot append Q&A.")
        return False
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [telegram_id, question, answer, timestamp]
        questions_sheet.append_row(row)
        logger.info(f"Q&A appended to Google Sheet for user {telegram_id}.")
        return True
    except Exception as e:
        logger.error(f"Failed to append Q&A to Google Sheet: {e}")
        return False

async def get_user_history_from_sheet(telegram_id: int) -> str:
    """Retrieves a user's Q&A history from the Google Sheet."""
    if not questions_sheet:
        return "History feature is currently unavailable."
    try:
        records = questions_sheet.get_all_records()
        user_answers = [
            f"Q: {record['question']}\nA: {record['answer']}\n({record['timestamp']})"
            for record in records if str(record.get('telegram_id')) == str(telegram_id)
        ]
        if user_answers:
            return "\n\n---\n\n".join(user_answers)
        else:
            return "No history found for you."
    except Exception as e:
        logger.error(f"Error fetching history for user {telegram_id}: {e}")
        return "An error occurred while fetching your history."

# Initialize on module load
init_google_sheets()
