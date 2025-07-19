import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.config import logger
from src.services.weather_service import WeatherService
from src.locale import get_message

weather_service = WeatherService()

async def get_weather_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the weather button callback."""
    query = update.callback_query
    await query.answer()
    await send_weather_update(query.message, context)

async def get_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /weather command."""
    await send_weather_update(update.message, context)

async def send_weather_update(message, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and sends the weather update."""
    lang = context.user_data.get('language', 'fa')

    weather_data = weather_service.get_weather()

    if weather_data:
        weather_text = get_message(
            "weather_report",
            lang,
            city=weather_data['city'],
            description=weather_data['description'],
            temp=weather_data['temperature']
        )
    else:
        weather_text = get_message("weather_error", lang)

    await update.message.reply_text(weather_text)
