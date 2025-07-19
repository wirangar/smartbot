import openai
import logging
import os
from pathlib import Path

from src.config import OPENAI_API_KEY, SYSTEM_PROMPT, logger

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logger.warning("OPENAI_API_KEY not set. OpenAI functionality will be disabled.")

async def get_ai_response(user_message: str, lang: str = 'fa') -> str | None:
    """Gets a response from OpenAI's chat model."""
    if not openai.api_key:
        logger.error("OpenAI API key is not configured.")
        return None

    # Append language context to the system prompt
    lang_prompt = f"Please respond in {lang}."
    full_system_prompt = f"{SYSTEM_PROMPT}\n{lang_prompt}"

    messages = [
        {"role": "system", "content": full_system_prompt},
        {"role": "user", "content": user_message}
    ]

    try:
        response = await openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.6, # Slightly lower temperature for more factual responses
            max_tokens=1500
        )
        ai_response = response.choices[0].message.content
        logger.info(f"Successfully received chat response from OpenAI for user message: '{user_message[:30]}...'")
        return ai_response
    except Exception as e:
        logger.error(f"Error calling OpenAI Chat API: {e}")
        return None

async def process_voice_message(voice_file_path: Path, lang: str = 'fa') -> str | None:
    """Transcribes a voice message using OpenAI's Whisper model."""
    if not openai.api_key:
        logger.error("OpenAI API key is not configured.")
        return None

    try:
        with open(voice_file_path, "rb") as audio_file:
            transcript = await openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=lang[:2] # Whisper uses 2-letter language codes (e.g., 'fa', 'en', 'it')
            )
        logger.info(f"Successfully transcribed voice message. Text: '{transcript.text[:50]}...'")
        return transcript.text
    except Exception as e:
        logger.error(f"Error calling OpenAI Whisper API: {e}")
        return None
    finally:
        # Clean up the temporary file
        if os.path.exists(voice_file_path):
            os.remove(voice_file_path)
            logger.info(f"Temporary voice file {voice_file_path} deleted.")
