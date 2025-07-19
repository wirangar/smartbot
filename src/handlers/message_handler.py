import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes

from src.config import ADMIN_CHAT_ID, logger
from src.services.openai_service import get_ai_response, process_voice_message
from src.services.google_sheets_service import append_qa_to_sheet
from src.utils.keyboard_builder import get_main_menu_keyboard
from src.handlers.user_manager import MAIN_MENU

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles incoming text messages from the user."""
    user_message = update.message.text
    user = update.effective_user
    lang = context.user_data.get('language', 'fa')

    # Check if this message is intended for the admin
    if context.user_data.get('next_message_is_admin_contact'):
        context.user_data['next_message_is_admin_contact'] = False
        if ADMIN_CHAT_ID:
            try:
                # Forward the user's message and add user info
                user_info = f"Message from: {user.full_name} (ID: {user.id})"
                await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=user_info)
                await context.bot.forward_message(chat_id=ADMIN_CHAT_ID, from_chat_id=user.id, message_id=update.message.message_id)

                success_text = {'fa': "پیام شما با موفقیت برای ادمین ارسال شد.", 'en': "Your message has been sent to the admin.", 'it': "Il tuo messaggio è stato inviato all'admin."}
                await update.message.reply_text(success_text.get(lang))
            except Exception as e:
                logger.error(f"Failed to forward message to admin: {e}")
                error_text = {'fa': "متاسفانه در ارسال پیام به ادمین خطایی رخ داد.", 'en': "Sorry, an error occurred while sending your message.", 'it': "Spiacenti, si è verificato un errore durante l'invio del messaggio."}
                await update.message.reply_text(error_text.get(lang))
        else:
            unavailable_text = {'fa': "قابلیت تماس با ادمین در حال حاضر فعال نیست.", 'en': "The contact admin feature is not currently active.", 'it': "La funzione di contatto admin non è attualmente attiva."}
            await update.message.reply_text(unavailable_text.get(lang))

        return MAIN_MENU

    # Process with OpenAI
    ai_response = await get_ai_response(user_message, lang)
    if ai_response:
        await append_qa_to_sheet(user.id, user_message, ai_response)
    else:
        error_text = {'fa': "متاسفم، مشکلی در پردازش پیام شما رخ داد. لطفاً از منوها استفاده کنید.", 'en': "I'm sorry, there was an issue processing your message. Please use the menus.", 'it': "Mi dispiace, si è verificato un problema nell'elaborare il tuo messaggio. Usa i menu."}
        ai_response = error_text.get(lang)

    await update.message.reply_text(ai_response, reply_markup=get_main_menu_keyboard(lang))
    return MAIN_MENU

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles incoming voice messages."""
    user = update.effective_user
    lang = context.user_data.get('language', 'fa')

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        # Define a temporary path to save the voice file
        temp_dir = Path("./temp_audio")
        temp_dir.mkdir(exist_ok=True)
        temp_voice_path = temp_dir / f"{update.message.voice.file_id}.ogg"

        await voice_file.download_to_drive(temp_voice_path)
        logger.info(f"Voice message from {user.id} saved to {temp_voice_path}")

        transcribed_text = await process_voice_message(temp_voice_path, lang)

        if transcribed_text:
            # Show transcription to user and process it as a text message
            feedback_text = {'fa': f"پیام شما: *{transcribed_text}*\nدرحال پردازش...", 'en': f"Your message: *{transcribed_text}*\nProcessing...", 'it': f"Il tuo messaggio: *{transcribed_text}*\nElaborazione..."}
            await update.message.reply_text(feedback_text.get(lang), parse_mode='Markdown')

            # Re-route the transcribed text to the text handler logic
            update.message.text = transcribed_text
            return await handle_text_message(update, context)
        else:
            error_text = {'fa': "متاسفم، نتوانستم پیام صوتی شما را پردازش کنم.", 'en': "I'm sorry, I couldn't process your voice message.", 'it': "Mi dispiace, non sono riuscito a elaborare il tuo messaggio vocale."}
            await update.message.reply_text(error_text.get(lang))

    except Exception as e:
        logger.error(f"Error handling voice message for user {user.id}: {e}")
        error_text = {'fa': "خطایی در پردازش پیام صوتی رخ داد.", 'en': "An error occurred while processing the voice message.", 'it': "Si è verificato un errore durante l'elaborazione del messaggio vocale."}
        await update.message.reply_text(error_text.get(lang))

    return MAIN_MENU
