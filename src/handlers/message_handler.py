import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.config import logger, ADMIN_CHAT_ID
from src.services.openai_service import get_ai_response, process_voice_message
from src.services.google_sheets_service import append_qa_to_sheet
from src.utils.keyboard_builder import get_main_menu_keyboard, get_item_keyboard
from src.utils.text_formatter import sanitize_markdown
from src.utils.paginator import Paginator
from src.services.search_engine import SearchEngine

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت پیام‌های متنی کاربر."""
    from src.handlers.user_manager import MAIN_MENU
    if 'language' not in context.user_data:
        await update.message.reply_text(
            sanitize_markdown("لطفاً ابتدا زبان خود را انتخاب کنید."),
            reply_markup=get_main_menu_keyboard('fa'),
            parse_mode='MarkdownV2'
        )
        return MAIN_MENU

    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'fa')
    user_message = update.message.text.strip()

    # بررسی پیام برای تماس با ادمین
    if context.user_data.get('next_message_is_admin_contact', False):
        if not ADMIN_CHAT_ID:
            error_text = {
                'fa': "شناسه ادمین تنظیم نشده است. لطفاً بعداً امتحان کنید.",
                'en': "Admin chat ID not configured. Please try again later.",
                'it': "ID chat admin non configurato. Riprova più tardi."
            }
            await update.message.reply_text(
                sanitize_markdown(error_text.get(lang)),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
        else:
            try:
                await context.bot.forward_message(ADMIN_CHAT_ID, update.message.chat_id, update.message.message_id)
                success_text = {
                    'fa': "پیام شما به ادمین ارسال شد.",
                    'en': "Your message was sent to the admin.",
                    'it': "Il tuo messaggio è stato inviato all'admin."
                }
                await update.message.reply_text(
                    sanitize_markdown(success_text.get(lang)),
                    parse_mode='MarkdownV2',
                    reply_markup=get_main_menu_keyboard(lang)
                )
            except Exception as e:
                logger.error(f"Error forwarding message to admin for user {user_id}: {e}")
                error_text = {
                    'fa': "خطایی در ارسال پیام به ادمین رخ داد.",
                    'en': "An error occurred while sending the message to the admin.",
                    'it': "Si è verificato un errore durante l'invio del messaggio all'admin."
                }
                await update.message.reply_text(
                    sanitize_markdown(error_text.get(lang)),
                    parse_mode='MarkdownV2',
                    reply_markup=get_main_menu_keyboard(lang)
                )
        context.user_data['next_message_is_admin_contact'] = False
        return MAIN_MENU

    # بررسی پیام برای جستجو
    if context.user_data.get('awaiting_search_query', False):
        search_engine = SearchEngine(Paginator())
        return await search_engine.search(update, context)

    # پردازش پیام متنی عمومی با OpenAI
    try:
        ai_response = await get_ai_response(user_message, lang)
        if ai_response:
            sanitized_response = sanitize_markdown(ai_response)
            await update.message.reply_text(
                sanitized_response,
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
            await append_qa_to_sheet(user_id, user_message, ai_response)
        else:
            error_text = {
                'fa': "متأسفم، نتوانستم پاسخی تولید کنم. لطفاً دوباره امتحان کنید.",
                'en': "Sorry, I couldn't generate a response. Please try again.",
                'it': "Mi dispiace, non sono riuscito a generare una risposta. Riprova."
            }
            await update.message.reply_text(
                sanitize_markdown(error_text.get(lang)),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
    except Exception as e:
        logger.error(f"Error processing text message for user {user_id}: {e}")
        error_text = {
            'fa': "خطایی در پردازش پیام شما رخ داد.",
            'en': "An error occurred while processing your message.",
            'it': "Si è verificato un errore durante l'elaborazione del tuo messaggio."
        }
        await update.message.reply_text(
            sanitize_markdown(error_text.get(lang)),
            parse_mode='MarkdownV2',
            reply_markup=get_main_menu_keyboard(lang)
        )

    return MAIN_MENU

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت پیام‌های صوتی."""
    from src.handlers.user_manager import MAIN_MENU
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'fa')

    if 'language' not in context.user_data:
        await update.message.reply_text(
            sanitize_markdown("لطفاً ابتدا زبان خود را انتخاب کنید."),
            reply_markup=get_main_menu_keyboard('fa'),
            parse_mode='MarkdownV2'
        )
        return MAIN_MENU

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        temp_dir = Path("./temp_audio")
        temp_dir.mkdir(exist_ok=True)
        temp_voice_path = temp_dir / f"{update.message.voice.file_id}.ogg"

        await voice_file.download_to_drive(temp_voice_path)
        logger.info(f"Voice message from {user_id} saved to {temp_voice_path}")

        transcribed_text = await process_voice_message(temp_voice_path, lang)

        if transcribed_text:
            feedback_text = {
                'fa': f"پیام شما: *{transcribed_text}*\nدرحال پردازش...",
                'en': f"Your message: *{transcribed_text}*\nProcessing...",
                'it': f"Il tuo messaggio: *{transcribed_text}*\nElaborazione..."
            }
            await update.message.reply_text(
                sanitize_markdown(feedback_text.get(lang)),
                parse_mode='MarkdownV2'
            )

            update.message.text = transcribed_text
            return await handle_text_message(update, context)
        else:
            error_text = {
                'fa': "متأسفم، نتوانستم پیام صوتی شما را پردازش کنم.",
                'en': "Sorry, I couldn't process your voice message.",
                'it': "Mi dispiace, non sono riuscito a elaborare il tuo messaggio vocale."
            }
            await update.message.reply_text(
                sanitize_markdown(error_text.get(lang)),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
    except Exception as e:
        logger.error(f"Error handling voice message for user {user_id}: {e}")
        error_text = {
            'fa': "خطایی در پردازش پیام صوتی رخ داد.",
            'en': "An error occurred while processing the voice message.",
            'it': "Si è verificato un errore durante l'elaborazione del messaggio vocale."
        }
        await update.message.reply_text(
            sanitize_markdown(error_text.get(lang)),
            parse_mode='MarkdownV2',
            reply_markup=get_main_menu_keyboard(lang)
        )
    finally:
        if temp_voice_path and temp_voice_path.exists():
            try:
                temp_voice_path.unlink()
                logger.info(f"Temporary voice file {temp_voice_path} deleted.")
            except Exception as e:
                logger.error(f"Failed to delete temporary voice file {temp_voice_path}: {e}")

    return MAIN_MENU
