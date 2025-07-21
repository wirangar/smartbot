import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
import aiohttp

from src.utils.keyboard_builder import get_main_menu_keyboard, get_item_keyboard, get_content_keyboard
from src.data.knowledge_base import get_content_by_path, search_knowledge_base
from src.utils.text_formatter import sanitize_markdown
from src.config import logger, ADMIN_CHAT_ID, OPENWEATHERMAP_API_KEY

# حالت مکالمه
from src.handlers.user_manager import MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی."""
    lang = context.user_data.get('language', 'fa')
    menu_text = {
        'fa': "لطفاً یک گزینه را از منوی اصلی انتخاب کنید:",
        'en': "Please select an option from the main menu:",
        'it': "Seleziona un'opzione dal menu principale:"
    }

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=menu_text.get(lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
    else:
        await update.message.reply_text(
            text=menu_text.get(lang),
            reply_markup=get_main_menu_keyboard(lang)
        )
    return MAIN_MENU

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت callbackهای منو."""
    query = update.callback_query
    await query.answer()

    path = query.data.split(":")[1:]
    lang = context.user_data.get('language', 'fa')

    if not path or path[0] == "main_menu":
        context.user_data['current_path'] = []
        await main_menu(update, context)
        return MAIN_MENU

    context.user_data['current_path'] = path

    if len(path) == 1:  # دسته‌بندی انتخاب شده
        category = path[0]
        category_text = {
            'fa': f"شما دسته‌بندی '{category}' را انتخاب کردید. لطفاً یک مورد را انتخاب کنید:",
            'en': f"You selected '{category}'. Please choose an item:",
            'it': f"Hai selezionato '{category}'. Scegli un elemento:"
        }
        await query.edit_message_text(
            text=category_text.get(lang),
            reply_markup=get_item_keyboard(category, lang)
        )

    elif len(path) == 2:  # آیتم انتخاب شده
        content, file_path = get_content_by_path(path, lang)
        sanitized_content = sanitize_markdown(content)

        await query.edit_message_text(
            text=sanitized_content,
            parse_mode='MarkdownV2',
            reply_markup=get_content_keyboard(path, lang)
        )

        if file_path:
            file_path = Path(file_path)
            if file_path.exists():
                try:
                    with open(file_path, 'rb') as file:
                        if file_path.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                            await context.bot.send_photo(chat_id=query.from_user.id, photo=file)
                        elif file_path.suffix.lower() == '.pdf':
                            await context.bot.send_document(chat_id=query.from_user.id, document=file)
                except Exception as e:
                    logger.error(f"Error sending file {file_path} for user {query.from_user.id}: {e}")
                    error_text = {
                        'fa': "خطایی در ارسال فایل رخ داد.",
                        'en': "An error occurred while sending the file.",
                        'it': "Si è verificato un errore durante l'invio del file."
                    }
                    await context.bot.send_message(chat_id=query.from_user.id, text=error_text.get(lang))
            else:
                logger.warning(f"File not found at path: {file_path}")
                not_found_text = {
                    'fa': "فایل مرتبط یافت نشد.",
                    'en': "Associated file not found.",
                    'it': "File associato non trovato."
                }
                await context.bot.send_message(chat_id=query.from_user.id, text=not_found_text.get(lang))

    return MAIN_MENU

async def main_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت دستور /menu."""
    await main_menu(update, context)
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت دستور /help."""
    lang = context.user_data.get('language', 'fa')
    help_text_map = {
        'fa': (
            "🤖 *راهنمای ربات Scholarino*\n\n"
            "- از منوها برای دسترسی به اطلاعات استفاده کنید.\n"
            "- برای جستجوی سریع، از گزینه 'جستجو' استفاده کنید.\n"
            "- برای بررسی آب‌وهوای پروجا، گزینه 'آب‌وهوا' را انتخاب کنید.\n"
            "- برای سوالات خاص، پیام خود را تایپ کنید.\n"
            "- برای تماس با مدیر، از دکمه 'تماس با ادمین' استفاده کنید."
        ),
        'en': (
            "🤖 *Scholarino Bot Help*\n\n"
            "- Use the menus to access information.\n"
            "- Use the 'Search' option for quick searches.\n"
            "- Check Perugia's weather with the 'Weather' option.\n"
            "- For specific questions, type your message.\n"
            "- Use the 'Contact Admin' button to reach the administrator."
        ),
        'it': (
            "🤖 *Aiuto Bot Scholarino*\n\n"
            "- Usa i menu per accedere alle informazioni.\n"
            "- Usa l'opzione 'Cerca' per ricerche rapide.\n"
            "- Controlla il meteo di Perugia con l'opzione 'Meteo'.\n"
            "- Per domande specifiche, digita il tuo messaggio.\n"
            "- Usa il pulsante 'Contatta Admin' per raggiungere l'amministratore."
        )
    }
    await update.message.reply_text(help_text_map.get(lang), parse_mode='Markdown', reply_markup=get_main_menu_keyboard(lang))
    return MAIN_MENU

async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت callbackهای دکمه‌های ثابت مثل جستجو، آب‌وهوا، پروفایل و غیره."""
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1]
    lang = context.user_data.get('language', 'fa')

    if action == "profile":
        from src.handlers.user_manager import show_profile
        await show_profile(update, context)
        return MAIN_MENU

    elif action == "contact_admin":
        context.user_data['next_message_is_admin_contact'] = True
        contact_text = {
            'fa': "لطفاً پیام خود را برای ارسال به ادمین تایپ کنید. پیام شما مستقیماً به ادمین ارسال خواهد شد.",
            'en': "Please type your message to the admin. It will be forwarded directly.",
            'it': "Scrivi il tuo messaggio per l'admin. Sarà inoltrato direttamente."
        }
        await query.edit_message_text(text=contact_text.get(lang))
        return MAIN_MENU

    elif action == "history":
        from src.services.google_sheets_service import get_user_history_from_sheet
        user_id = query.from_user.id
        try:
            history = await get_user_history_from_sheet(user_id)
            history_text_map = {
                'fa': history if history != "No history found." else "📜 تاریخچه‌ای برای شما یافت نشد.",
                'en': history if history != "No history found." else "📜 No history found for you.",
                'it': history if history != "No history found." else "📜 Nessuna cronologia trovata per te."
            }
            await query.edit_message_text(history_text_map.get(lang), reply_markup=get_main_menu_keyboard(lang))
        except Exception as e:
            logger.error(f"Error fetching history for user {user_id}: {e}")
            error_text = {
                'fa': "خطایی در دریافت تاریخچه رخ داد.",
                'en': "An error occurred while fetching your history.",
                'it': "Si è verificato un errore durante il recupero della cronologia."
            }
            await query.edit_message_text(error_text.get(lang), reply_markup=get_main_menu_keyboard(lang))
        return MAIN_MENU

    elif action == "help":
        help_text_map = {
            'fa': (
                "🤖 *راهنمای ربات Scholarino*\n\n"
                "- از منوها برای دسترسی به اطلاعات استفاده کنید.\n"
                "- برای جستجوی سریع، از گزینه 'جستجو' استفاده کنید.\n"
                "- برای بررسی آب‌وهوای پروجا، گزینه 'آب‌وهوا' را انتخاب کنید.\n"
                "- برای سوالات خاص، پیام خود را تایپ کنید.\n"
                "- برای تماس با مدیر، از دکمه 'تماس با ادمین' استفاده کنید."
            ),
            'en': (
                "🤖 *Scholarino Bot Help*\n\n"
                "- Use the menus to access information.\n"
                "- Use the 'Search' option for quick searches.\n"
                "- Check Perugia's weather with the 'Weather' option.\n"
                "- For specific questions, type your message.\n"
                "- Use the 'Contact Admin' button to reach the administrator."
            ),
            'it': (
                "🤖 *Aiuto Bot Scholarino*\n\n"
                "- Usa i menu per accedere alle informazioni.\n"
                "- Usa l'opzione 'Cerca' per ricerche rapide.\n"
                "- Controlla il meteo di Perugia con l'opzione 'Meteo'.\n"
                "- Per domande specifiche, digita il tuo messaggio.\n"
                "- Usa il pulsante 'Contatta Admin' per raggiungere l'amministratore."
            )
        }
        await query.edit_message_text(help_text_map.get(lang), parse_mode='Markdown', reply_markup=get_main_menu_keyboard(lang))
        return MAIN_MENU

    elif action == "search":
        context.user_data['awaiting_search_query'] = True
        search_text = {
            'fa': "لطفاً عبارت موردنظر خود را برای جستجو تایپ کنید:",
            'en': "Please type your search query:",
            'it': "Digita la tua query di ricerca:"
        }
        await query.edit_message_text(search_text.get(lang))
        return MAIN_MENU

    elif action == "weather":
        if not OPENWEATHERMAP_API_KEY:
            error_text = {
                'fa': "API آب‌وهوا تنظیم نشده است. لطفاً با ادمین تماس بگیرید.",
                'en': "Weather API not configured. Please contact the admin.",
                'it': "API meteo non configurata. Contatta l'admin."
            }
            await query.edit_message_text(error_text.get(lang), reply_markup=get_main_menu_keyboard(lang))
            return MAIN_MENU

        async with aiohttp.ClientSession() as session:
            url = f"http://api.openweathermap.org/data/2.5/weather?q=Perugia,IT&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang={lang}"
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Weather API error: Status {response.status}")
                        error_text = {
                            'fa': "خطایی در دریافت اطلاعات آب‌وهوا رخ داد.",
                            'en': "An error occurred while fetching weather data.",
                            'it': "Si è verificato un errore durante il recupero dei dati meteo."
                        }
                        await query.edit_message_text(error_text.get(lang), reply_markup=get_main_menu_keyboard(lang))
                        return MAIN_MENU

                    data = await response.json()
                    weather = data['weather'][0]['description']
                    temp = data['main']['temp']
                    feels_like = data['main']['feels_like']
                    humidity = data['main']['humidity']
                    wind_speed = data['wind']['speed']
                    sunrise = data['sys']['sunrise']
                    sunset = data['sys']['sunset']

                    from datetime import datetime
                    sunrise_time = datetime.fromtimestamp(sunrise).strftime("%H:%M")
                    sunset_time = datetime.fromtimestamp(sunset).strftime("%H:%M")

                    weather_text = {
                        'fa': (
                            f"🌦 *وضعیت آب‌وهوا در پروجا*\n\n"
                            f"وضعیت: {weather}\n"
                            f"دما: {temp}°C\n"
                            f"حس می‌شود: {feels_like}°C\n"
                            f"رطوبت: {humidity}%\n"
                            f"سرعت باد: {wind_speed} متر/ثانیه\n"
                            f"طلوع آفتاب: {sunrise_time}\n"
                            f"غروب آفتاب: {sunset_time}"
                        ),
                        'en': (
                            f"🌦 *Weather in Perugia*\n\n"
                            f"Condition: {weather}\n"
                            f"Temperature: {temp}°C\n"
                            f"Feels like: {feels_like}°C\n"
                            f"Humidity: {humidity}%\n"
                            f"Wind speed: {wind_speed} m/s\n"
                            f"Sunrise: {sunrise_time}\n"
                            f"Sunset: {sunset_time}"
                        ),
                        'it': (
                            f"🌦 *Meteo a Perugia*\n\n"
                            f"Condizione: {weather}\n"
                            f"Temperatura: {temp}°C\n"
                            f"Percepita: {feels_like}°C\n"
                            f"Umidità: {humidity}%\n"
                            f"Velocità del vento: {wind_speed} m/s\n"
                            f"Alba: {sunrise_time}\n"
                            f"Tramonto: {sunset_time}"
                        )
                    }
                    await query.edit_message_text(
                        sanitize_markdown(weather_text.get(lang)),
                        parse_mode='MarkdownV2',
                        reply_markup=get_main_menu_keyboard(lang)
                    )
            except Exception as e:
                logger.error(f"Error fetching weather data: {e}")
                error_text = {
                    'fa': "خطایی در دریافت اطلاعات آب‌وهوا رخ داد.",
                    'en': "An error occurred while fetching weather data.",
                    'it': "Si è verificato un errore durante il recupero dei dati meteo."
                }
                await query.edit_message_text(error_text.get(lang), reply_markup=get_main_menu_keyboard(lang))

        return MAIN_MENU
