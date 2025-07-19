import requests
import logging
from src.config import os, logger

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv("WEATHER_API_KEY")
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"

    def get_weather(self, city: str = "Perugia") -> dict | None:
        """Fetches weather data for a given city."""
        if not self.api_key:
            logger.warning("WEATHER_API_KEY is not set. Weather service is disabled.")
            return None

        params = {
            'q': city,
            'appid': self.api_key,
            'units': 'metric',
            'lang': 'fa' # Default to Persian for descriptions
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status() # Raise an exception for bad status codes
            data = response.json()

            weather_info = {
                'description': data['weather'][0]['description'],
                'temperature': data['main']['temp'],
                'city': data['name']
            }
            logger.info(f"Successfully fetched weather for {city}.")
            return weather_info
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather data: {e}")
            return None
        except KeyError:
            logger.error("Unexpected response format from weather API.")
            return None
