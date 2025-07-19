import openai
import logging
from config import OPENAI_API_KEY, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logger.warning("OPENAI_API_KEY not set. OpenAI functionality will be disabled.")

async def get_ai_response(user_message: str) -> str | None:
    if not openai.api_key:
        logger.error("OpenAI API key is not configured.")
        return None

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]

    try:
        response = await openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        ai_response = response.choices[0].message.content
        logger.info(f"Successfully received response from OpenAI for user message: '{user_message[:30]}...'")
        return ai_response
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return None
