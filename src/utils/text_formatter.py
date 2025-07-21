import logging
import re
from typing import Optional

from src.config import logger

def escape_markdown_v2(text: str) -> str:
    """
    فرمت‌بندی متن برای MarkdownV2 تلگرام با اسکیپ کردن کاراکترهای خاص.
    """
    if not text:
        return text
    
    # لیست کاراکترهای خاص که نیاز به اسکیپ دارند
    special_chars = r'[_*[\]()~`>#+\-=|{}.!]'
    
    # اسکیپ کردن کاراکترهای خاص
    escaped_text = re.sub(r'([%s])' % special_chars, r'\\\1', text)
    
    # جایگزینی \n با \n\n برای فاصله‌گذاری بهتر در تلگرام
    escaped_text = escaped_text.replace('\n', '\n\n')
    
    logger.debug(f"Escaped MarkdownV2 text: {escaped_text[:100]}...")
    return escaped_text

def sanitize_markdown(text: str, max_length: int = 4096) -> str:
    """
    آماده‌سازی متن برای ارسال در تلگرام با فرمت MarkdownV2.
    """
    try:
        # حذف کاراکترهای غیرمجاز یا نامناسب
        text = text.replace('\r', '')  # حذف carriage return
        text = re.sub(r'[^\x00-\x7F\u0600-\u06FF]', '', text)  # حذف کاراکترهای غیر UTF-8 و غیرفارسی
        
        # اسکیپ کردن برای MarkdownV2
        sanitized_text = escape_markdown_v2(text)
        
        # کوتاه کردن متن اگر بیش از حد طولانی باشد
        if len(sanitized_text) > max_length:
            sanitized_text = sanitized_text[:max_length - 3] + '...'
            logger.warning(f"Text truncated to {max_length} characters.")
        
        return sanitized_text
    except Exception as e:
        logger.error(f"Error sanitizing Markdown text: {e}")
        return escape_markdown_v2("An error occurred while formatting the text.")

def format_bold(text: str, lang: str = 'fa') -> str:
    """
    فرمت‌بندی متن به‌صورت بولد.
    """
    try:
        return f"*{escape_markdown_v2(text)}*"
    except Exception as e:
        logger.error(f"Error formatting bold text: {e}")
        return text

def format_italic(text: str, lang: str = 'fa') -> str:
    """
    فرمت‌بندی متن به‌صورت ایتالیک.
    """
    try:
        return f"_{escape_markdown_v2(text)}_"
    except Exception as e:
        logger.error(f"Error formatting italic text: {e}")
        return text

def format_list(items: list, lang: str = 'fa') -> str:
    """
    فرمت‌بندی لیست آیتم‌ها به‌صورت شماره‌گذاری‌شده.
    """
    try:
        formatted_items = [
            f"{i+1}\\. {escape_markdown_v2(item)}" for i, item in enumerate(items)
        ]
        return "\n".join(formatted_items)
    except Exception as e:
        logger.error(f"Error formatting list: {e}")
        return "\n".join(items)
