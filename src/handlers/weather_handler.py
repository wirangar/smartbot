import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.config import logger
from src.services.weather_service import WeatherService
from src.locale import get_message

weather_service = WeatherService()

async def get_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /weather command and sends the current weather in Perugia."""
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
