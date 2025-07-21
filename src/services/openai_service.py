import logging
from pathlib import Path
from typing import Optional
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import logger, OPENAI_API_KEY

# تنظیم کلید API
openai.api_key = OPENAI_API_KEY

# پرامپت سیستمی برای پاسخ‌های متنی
SYSTEM_PROMPT = (
    "You are Scholarino, a helpful assistant for students in Perugia, Italy. "
    "Provide accurate and concise answers related to living and studying in Perugia. "
    "If the question is unrelated, respond politely and suggest focusing on relevant topics. "
    "Always respond in the user's selected language."
)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_ai_response(user_message: str, lang: str = 'fa') -> Optional[str]:
    """
    دریافت پاسخ از OpenAI Chat API برای پیام متنی کاربر.
    """
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key is not configured.")
        return None

    # نگاشت کد زبان برای OpenAI
    lang_map = {'fa': 'Persian', 'en': 'English', 'it': 'Italian'}
    lang_prompt = f"Please respond in {lang_map.get(lang, 'English')}."
    full_system_prompt = f"{SYSTEM_PROMPT}\n{lang_prompt}"

    messages = [
        {"role": "system", "content": full_system_prompt},
        {"role": "user", "content": user_message}
    ]

    try:
        response = await openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.6,
            max_tokens=1500
        )
        ai_response = response.choices[0].message.content
        logger.info(f"Successfully received chat response from OpenAI for user message: '{user_message[:30]}...'")
        return ai_response
    except Exception as e:
        logger.error(f"Error calling OpenAI Chat API: {e}")
        return None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def process_voice_message(voice_file_path: Path, lang: str = 'fa') -> Optional[str]:
    """
    تبدیل پیام صوتی به متن با استفاده از OpenAI Whisper API.
    """
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key is not configured.")
        return None

    # نگاشت کد زبان برای Whisper API
    LANGUAGE_CODES = {
        'fa': 'fa',
        'en': 'en',
        'it': 'it'
    }

    try:
        with open(voice_file_path, "rb") as audio_file:
            transcript = await openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=LANGUAGE_CODES.get(lang, 'en')
            )
            logger.info(f"Successfully transcribed voice message. Text: '{transcript.text[:50]}...'")
            return transcript.text
    except Exception as e:
        logger.error(f"Error calling OpenAI Whisper API: {e}")
        return None
