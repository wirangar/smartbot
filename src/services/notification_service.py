import asyncio
import logging
from datetime import datetime, timedelta

from telegram.ext import Application

from src.config import logger
from src.data.knowledge_base import get_knowledge_base
from src.database import get_db_cursor

async def check_deadlines_and_notify(application: Application):
    """
    Checks for upcoming deadlines and notifies subscribed users.
    This function is intended to be run as a daily job.
    """
    logger.info("Running daily deadline check...")
    kb = get_knowledge_base()
    now = datetime.now()

    # Define notification windows (e.g., 7, 3, 1 day before)
    notification_windows = [7, 3, 1]

    # Find all deadline items in the knowledge base
    all_deadlines = []
    for category in kb.values():
        for item in category:
            if item.get('id') == 'academic_calendar' and 'subsections' in item:
                for sub in item['subsections']:
                    if sub.get('title', {}).get('en') == 'Important Deadlines':
                        # This is a very specific way to find deadlines.
                        # A better approach would be a dedicated 'deadlines' key in the JSON.
                        for deadline_str in sub.get('content', {}).get('en', []):
                            try:
                                # Example format: "ADiSU Scholarship Application Deadline: September 15, 2025"
                                event, date_str = deadline_str.split(':')
                                deadline_date = datetime.strptime(date_str.strip(), "%B %d, %Y")
                                all_deadlines.append({'event': event.strip(), 'date': deadline_date})
                            except (ValueError, IndexError):
                                continue

    if not all_deadlines:
        logger.info("No deadlines found in the knowledge base.")
        return

    # Get all subscribed users from the database
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT telegram_id, first_name, language FROM users WHERE is_subscribed_to_notifications = TRUE")
            subscribed_users = cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch subscribed users: {e}")
        return

    logger.info(f"Found {len(subscribed_users)} subscribed users.")

    for deadline in all_deadlines:
        time_until = deadline['date'] - now

        if time_until.days + 1 in notification_windows:
            days_left = time_until.days + 1
            logger.info(f"Deadline '{deadline['event']}' is in {days_left} days. Notifying users.")

            for user_id, first_name, lang in subscribed_users:
                message_templates = {
                    'fa': (
                        f"🔔 *یادآوری مهم از Scholarino*\n\n"
                        f"سلام {first_name} عزیز،\n\n"
                        f"فقط **{days_left} روز** تا پایان مهلت **{deadline['event']}** فرصت باقیست!\n\n"
                        f"🗓️ *تاریخ نهایی:* {deadline['date'].strftime('%Y-%m-%d')}\n\n"
                        "فراموش نکنید که مدارک خود را آماده و درخواست خود را نهایی کنید."
                    ),
                    'en': (
                        f"🔔 *Important Reminder from Scholarino*\n\n"
                        f"Hi {first_name},\n\n"
                        f"There are only **{days_left} days** left until the **{deadline['event']}** deadline!\n\n"
                        f"🗓️ *Final Date:* {deadline['date'].strftime('%Y-%m-%d')}\n\n"
                        "Don't forget to prepare your documents and finalize your application."
                    ),
                    'it': (
                        f"🔔 *Promemoria Importante da Scholarino*\n\n"
                        f"Ciao {first_name},\n\n"
                        f"Mancano solo **{days_left} giorni** alla scadenza per **{deadline['event']}**!\n\n"
                        f"🗓️ *Data Finale:* {deadline['date'].strftime('%Y-%m-%d')}\n\n"
                        "Non dimenticare di preparare i documenti e finalizzare la tua domanda."
                    )
                }

                message = message_templates.get(lang, message_templates['en'])
                try:
                    await application.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
                    logger.info(f"Sent deadline notification to user {user_id}.")
                except Exception as e:
                    logger.error(f"Failed to send deadline notification to user {user_id}: {e}")
                await asyncio.sleep(0.1) # Avoid hitting rate limits

async def start_notification_job(application: Application):
    """Adds the daily deadline check job to the application's job queue."""
    job_queue = application.job_queue
    # Run daily at a specific time, e.g., 10:00 AM UTC
    job_queue.run_daily(check_deadlines_and_notify, time=timedelta(hours=10), job_kwargs={'application': application})
    logger.info("Daily notification job scheduled.")
