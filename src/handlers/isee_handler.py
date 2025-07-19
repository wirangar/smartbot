import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from src.config import logger
from src.database import get_db_cursor
from src.locale import get_message
from src.services.isee_service import calculate_isee
from src.handlers.user_manager import MAIN_MENU

# Conversation states
INCOME, PROPERTY, FAMILY, CONFIRM = range(4)

async def start_isee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the ISEE calculation conversation."""
    lang = context.user_data.get('language', 'fa')

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(get_message("start_isee", lang))
    else: # Started via /isee command
        await update.message.reply_text(get_message("start_isee", lang))

    return INCOME

async def handle_income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's income input."""
    lang = context.user_data.get('language', 'fa')
    try:
        income = float(update.message.text)
        if income < 0: raise ValueError
        context.user_data['isee_income'] = income
        await update.message.reply_text(get_message("ask_property", lang))
        return PROPERTY
    except (ValueError, TypeError):
        await update.message.reply_text(get_message("invalid_number", lang))
        return INCOME

async def handle_property(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's property value input."""
    lang = context.user_data.get('language', 'fa')
    try:
        property_val = float(update.message.text)
        if property_val < 0: raise ValueError
        context.user_data['isee_property'] = property_val
        await update.message.reply_text(get_message("ask_family", lang))
        return FAMILY
    except (ValueError, TypeError):
        await update.message.reply_text(get_message("invalid_number", lang))
        return PROPERTY

async def handle_family(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the family members input and shows confirmation."""
    lang = context.user_data.get('language', 'fa')
    try:
        family_members = int(update.message.text)
        if family_members < 1: raise ValueError
        context.user_data['isee_family'] = family_members

        # Calculate ISEE
        income = context.user_data['isee_income']
        prop = context.user_data['isee_property']
        isee_value = calculate_isee(income, prop, family_members)
        context.user_data['isee_value'] = isee_value

        # Confirmation keyboard
        keyboard = [[
            InlineKeyboardButton(get_message("yes", lang), callback_data="isee_confirm:yes"),
            InlineKeyboardButton(get_message("no", lang), callback_data="isee_confirm:no")
        ]]

        await update.message.reply_text(
            get_message("confirm_isee", lang, income=income, property=prop, family=family_members, isee_value=isee_value),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return CONFIRM
    except (ValueError, TypeError):
        await update.message.reply_text(get_message("invalid_family", lang))
        return FAMILY

async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the final confirmation from the user."""
    query = update.callback_query
    await query.answer()
    choice = query.data.split(":")[1]
    lang = context.user_data.get('language', 'fa')
    user_id = query.from_user.id

    if choice == 'yes':
        isee_value = context.user_data.get('isee_value', 0.0)
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO isee_calculations (user_id, isee_value) VALUES (%s, %s)",
                    (user_id, isee_value)
                )
            await query.edit_message_text(get_message("isee_saved", lang))
        except Exception as e:
            logger.error(f"Failed to save ISEE for user {user_id}: {e}")
            await query.edit_message_text(get_message("isee_cancelled", lang)) # Inform user of failure
    else:
        await query.edit_message_text(get_message("isee_cancelled", lang))

    # Clean up user_data
    for key in ['isee_income', 'isee_property', 'isee_family', 'isee_value']:
        context.user_data.pop(key, None)

    return ConversationHandler.END

async def cancel_isee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the ISEE calculation conversation."""
    lang = context.user_data.get('language', 'fa')
    await update.message.reply_text(get_message("isee_cancelled", lang))
    # Clean up user_data
    for key in ['isee_income', 'isee_property', 'isee_family', 'isee_value']:
        context.user_data.pop(key, None)
    return ConversationHandler.END
