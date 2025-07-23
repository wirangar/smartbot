import logging
import json
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationHandlerStop, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from src.config import logger
from src.utils.text_formatter import sanitize_markdown
from src.database import get_db_cursor
from src.handlers.user_manager import MAIN_MENU, get_main_menu_keyboard

class ISEEState(Enum):
    FAMILY = 1
    INCOME = 2
    PROPERTY = 3
    PROPERTY_SIZE = 4

class ISEEService:
    def __init__(self, json_data: dict, db_manager):
        self.data = json_data
        self.db = db_manager
        self.scholarship_limit = None
        self._setup_isee_parameters()

    def _setup_isee_parameters(self):
        """Extract ISEE limit from knowledge base."""
        try:
            scholarship_section = self.data.get("بورسیه و تقویم آموزشی", [])
            for item in scholarship_section:
                if "توضیح کامل عدد ISEE" in item.get("title", ""):
                    content = item.get("content", [])
                    for line in content:
                        if "سقف ISEE" in line or "حداکثر" in line:
                            if "€" in line:
                                self.scholarship_limit = float(line.split("€")[-1].replace(",", "").strip())
                                logger.info(f"ISEE limit set to: {self.scholarship_limit}")
                                return
            self.scholarship_limit = 27948.60  # Default for 2025/2026
            logger.info(f"Using default ISEE limit: {self.scholarship_limit}")
        except Exception as e:
            logger.error(f"Error setting up ISEE parameters: {e}")
            self.scholarship_limit = 27948.60

    def calculate(self, family_members: int, annual_income: float, 
                 property_status: str, property_size: float = 0) -> dict:
        """Calculate ISEE value and scholarship eligibility."""
        try:
            # Family size parameters
            family_params = {1: 1.00, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85}
            scale = family_params.get(family_members, 2.85 + 0.35 * (family_members - 5))
            
            # Calculate property value
            property_value = property_size * 500 * 0.2 if property_status == "مالک" else 0
            total_assets = annual_income + property_value
            isee_value = round(total_assets / scale, 2)

            # Determine scholarship status
            if isee_value <= self.scholarship_limit * 0.55:
                status = {"fa": "بورسیه کامل", "en": "Full scholarship", "it": "Borsa completa"}
                amount = 5192
                suggestion = {
                    "fa": "شما واجد شرایط حداکثر کمک هزینه (5192 یورو + خوابگاه رایگان) هستید.",
                    "en": "You are eligible for the maximum scholarship (5192 EUR + free dormitory).",
                    "it": "Sei idoneo per la borsa massima (5192 EUR + dormitorio gratuito)."
                }
            elif isee_value <= self.scholarship_limit * 0.715:
                status = {"fa": "بورسیه متوسط", "en": "Medium scholarship", "it": "Borsa media"}
                amount = 3634
                suggestion = {
                    "fa": "شما واجد شرایط بورسیه متوسط (3634 یورو) هستید.",
                    "en": "You are eligible for a medium scholarship (3634 EUR).",
                    "it": "Sei idoneo per una borsa media (3634 EUR)."
                }
            elif isee_value <= self.scholarship_limit:
                status = {"fa": "بورسیه جزئی", "en": "Partial scholarship", "it": "Borsa parziale"}
                amount = 2000
                suggestion = {
                    "fa": "شما واجد شرایط بورسیه جزئی (2000 یورو) هستید.",
                    "en": "You are eligible for a partial scholarship (2000 EUR).",
                    "it": "Sei idoneo per una borsa parziale (2000 EUR)."
                }
            else:
                status = {"fa": "عدم واجد شرایط", "en": "Not eligible", "it": "Non idoneo"}
                amount = 0
                suggestion = {
                    "fa": "برای گزینه‌های دیگر با دانشگاه مشورت کنید.",
                    "en": "Consult the university for other options.",
                    "it": "Consulta l'università per altre opzioni."
                }

            return {
                'value': isee_value,
                'status': status,
                'amount': amount,
                'details': {
                    'family_members': family_members,
                    'annual_income': annual_income,
                    'property_status': property_status,
                    'property_size': property_size if property_status == "مالک" else 0
                },
                'suggestion': suggestion,
                'limit': self.scholarship_limit
            }
        except Exception as e:
            logger.error(f"Error calculating ISEE: {e}")
            raise

    def get_conversation_handler(self):
        """Return ConversationHandler for ISEE calculation."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start, pattern="^menu:محاسبه ISEE$|^menu:Calculate ISEE$|^menu:Calcola ISEE$")
            ],
            states={
                ISEEState.FAMILY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_family)],
                ISEEState.INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_income)],
                ISEEState.PROPERTY: [CallbackQueryHandler(self.handle_property)],
                ISEEState.PROPERTY_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_property_size)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            map_to_parent={ConversationHandler.END: MAIN_MENU}
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the ISEE calculation process."""
        query = update.callback_query
        await query.answer()
        lang = context.user_data.get('language', 'fa')
        messages = {
            'fa': "📊 *محاسبه عدد ISEE برای بورسیه*\n\nلطفاً تعداد اعضای خانواده خود را وارد کنید:",
            'en': "📊 *Calculate ISEE for scholarship*\n\nPlease enter the number of family members:",
            'it': "📊 *Calcolo ISEE per la borsa di studio*\n\nInserisci il numero di membri della famiglia:"
        }
        await query.message.reply_text(
            text=sanitize_markdown(messages[lang]),
            parse_mode='MarkdownV2'
        )
        return ISEEState.FAMILY

    async def handle_family(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle family members input."""
        try:
            members = int(update.message.text)
            if members < 1:
                raise ValueError("Number of family members must be at least 1")
            context.user_data['isee'] = {'family_members': members}
            lang = context.user_data.get('language', 'fa')
            messages = {
                'fa': "لطفاً درآمد سالانه خانواده به یورو را وارد کنید:\n(برای تبدیل تومان به یورو: مبلغ تومان ÷ ۳۵۰۰۰)",
                'en': "Please enter the annual family income in euros:\n(To convert IRR to EUR: amount ÷ 35000)",
                'it': "Inserisci il reddito annuo familiare in euro:\n(Per convertire IRR in EUR: importo ÷ 35000)"
            }
            await update.message.reply_text(
                text=sanitize_markdown(messages[lang]),
                parse_mode='MarkdownV2'
            )
            return ISEEState.INCOME
        except ValueError:
            lang = context.user_data.get('language', 'fa')
            errors = {
                'fa': "❌ لطفاً عدد صحیح معتبر وارد کنید.",
                'en': "❌ Please enter a valid integer.",
                'it': "❌ Inserisci un numero intero valido."
            }
            await update.message.reply_text(
                text=sanitize_markdown(errors[lang]),
                parse_mode='MarkdownV2'
            )
            return ISEEState.FAMILY

    async def handle_income(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle annual income input."""
        try:
            income = float(update.message.text)
            if income < 0:
                raise ValueError("Income cannot be negative")
            context.user_data['isee']['annual_income'] = income
            lang = context.user_data.get('language', 'fa')
            buttons = {
                'fa': ["مالک", "مستأجر"],
                'en': ["Owner", "Tenant"],
                'it': ["Proprietario", "Inquilino"]
            }
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton(buttons[lang][0], callback_data="مالک")],
                [InlineKeyboardButton(buttons[lang][1], callback_data="مستأجر")]
            ])
            messages = {
                'fa': "وضعیت ملک خود را انتخاب کنید:",
                'en': "Select your property status:",
                'it': "Seleziona lo stato della tua proprietà:"
            }
            await update.message.reply_text(
                text=sanitize_markdown(messages[lang]),
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )
            return ISEEState.PROPERTY
        except ValueError:
            lang = context.user_data.get('language', 'fa')
            errors = {
                'fa': "❌ لطفاً عدد معتبر وارد کنید.",
                'en': "❌ Please enter a valid number.",
                'it': "❌ Inserisci un numero valido."
            }
            await update.message.reply_text(
                text=sanitize_markdown(errors[lang]),
                parse_mode='MarkdownV2'
            )
            return ISEEState.INCOME

    async def handle_property(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle property status selection."""
        query = update.callback_query
        await query.answer()
        status = query.data
        if status not in ["مالک", "مستأجر"]:
            lang = context.user_data.get('language', 'fa')
            errors = {
                'fa': "❌ لطفاً گزینه معتبر انتخاب کنید.",
                'en': "❌ Please select a valid option.",
                'it': "❌ Seleziona un'opzione valida."
            }
            await query.message.reply_text(
                text=sanitize_markdown(errors[lang]),
                parse_mode='MarkdownV2'
            )
            return ISEEState.PROPERTY
        context.user_data['isee']['property_status'] = status
        if status == "مالک":
            lang = context.user_data.get('language', 'fa')
            messages = {
                'fa': "لطفاً متراژ ملک (متر مربع) را وارد کنید:",
                'en': "Please enter the property size (square meters):",
                'it': "Inserisci la dimensione della proprietà (metri quadrati):"
            }
            await query.message.reply_text(
                text=sanitize_markdown(messages[lang]),
                parse_mode='MarkdownV2'
            )
            return ISEEState.PROPERTY_SIZE
        return await self.finish(update, context)

    async def handle_property_size(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle property size input."""
        try:
            size = float(update.message.text)
            if size < 0:
                raise ValueError("Property size cannot be negative")
            context.user_data['isee']['property_size'] = size
            return await self.finish(update, context)
        except ValueError:
            lang = context.user_data.get('language', 'fa')
            errors = {
                'fa': "❌ لطفاً عدد معتبر وارد کنید.",
                'en': "❌ Please enter a valid number.",
                'it': "❌ Inserisci un numero valido."
            }
            await update.message.reply_text(
                text=sanitize_markdown(errors[lang]),
                parse_mode='MarkdownV2'
            )
            return ISEEState.PROPERTY_SIZE

    async def finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Complete ISEE calculation and display results."""
        data = context.user_data.get('isee', {})
        try:
            result = self.calculate(
                family_members=data['family_members'],
                annual_income=data['annual_income'],
                property_status=data.get('property_status', 'مستأجر'),
                property_size=data.get('property_size', 0)
            )
            lang = context.user_data.get('language', 'fa')
            property_line = {
                'fa': f"📏 متراژ ملک: {result['details']['property_size']} متر" if result['details']['property_status'] == 'مالک' else '',
                'en': f"📏 Property size: {result['details']['property_size']} sqm" if result['details']['property_status'] == 'مالک' else '',
                'it': f"📏 Dimensione proprietà: {result['details']['property_size']} mq" if result['details']['property_status'] == 'مالک' else ''
            }
            messages = {
                'fa': (
                    f"📊 *نتایج محاسبه ISEE*:\n\n"
                    f"👨‍👩‍👧‍👦 اعضای خانواده: {result['details']['family_members']}\n"
                    f"💰 درآمد سالانه: {result['details']['annual_income']} یورو\n"
                    f"🏠 وضعیت ملک: {result['details']['property_status']}\n"
                    f"{property_line['fa']}\n\n"
                    f"📊 عدد ISEE شما: {result['value']} یورو\n"
                    f"🏆 وضعیت بورسیه: {result['status']['fa']} ({result['amount']} یورو)\n"
                    f"💡 پیشنهاد: {result['suggestion']['fa']}\n\n"
                    f"ℹ️ سقف مجاز: {result['limit']} یورو"
                ),
                'en': (
                    f"📊 *ISEE Calculation Results*:\n\n"
                    f"👨‍👩‍👧‍👦 Family members: {result['details']['family_members']}\n"
                    f"💰 Annual income: {result['details']['annual_income']} EUR\n"
                    f"🏠 Property status: {result['details']['property_status']}\n"
                    f"{property_line['en']}\n\n"
                    f"📊 Your ISEE: {result['value']} EUR\n"
                    f"🏆 Scholarship status: {result['status']['en']} ({result['amount']} EUR)\n"
                    f"💡 Suggestion: {result['suggestion']['en']}\n\n"
                    f"ℹ️ Maximum limit: {result['limit']} EUR"
                ),
                'it': (
                    f"📊 *Risultati Calcolo ISEE*:\n\n"
                    f"👨‍👩‍👧‍👦 Membri della famiglia: {result['details']['family_members']}\n"
                    f"💰 Reddito annuo: {result['details']['annual_income']} EUR\n"
                    f"🏠 Stato della proprietà: {result['details']['property_status']}\n"
                    f"{property_line['it']}\n\n"
                    f"📊 Il tuo ISEE: {result['value']} EUR\n"
                    f"🏆 Stato della borsa: {result['status']['it']} ({result['amount']} EUR)\n"
                    f"💡 Suggerimento: {result['suggestion']['it']}\n\n"
                    f"ℹ️ Limite massimo: {result['limit']} EUR"
                )
            }

            # Save to database
            with get_db_cursor() as cur:
                cur.execute(
                    "INSERT INTO isee_calculations (user_id, isee_value) VALUES (%s, %s)",
                    (update.effective_user.id, result['value'])
                )
                cur.execute(
                    "INSERT INTO sessions (session_id, user_id, data) VALUES (%s, %s, %s)",
                    (f"isee_{update.effective_user.id}_{int(result['value'])}", 
                     update.effective_user.id, 
                     json.dumps(result, ensure_ascii=False))
                )

            await (update.message or update.callback_query.message).reply_text(
                text=sanitize_markdown(messages[lang]),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
            context.user_data.clear()
            return MAIN_MENU
        except Exception as e:
            logger.error(f"Error finishing ISEE calculation: {e}")
            lang = context.user_data.get('language', 'fa')
            errors = {
                'fa': "❌ خطایی در محاسبه ISEE رخ داد. لطفاً دوباره امتحان کنید.",
                'en': "❌ An error occurred during ISEE calculation. Please try again.",
                'it': "❌ Si è verificato un errore durante il calcolo ISEE. Riprova."
            }
            await (update.message or update.callback_query.message).reply_text(
                text=sanitize_markdown(errors[lang]),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
            return MAIN_MENU

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the ISEE calculation process."""
        lang = context.user_data.get('language', 'fa')
        messages = {
            'fa': "❌ محاسبه ISEE لغو شد.",
            'en': "❌ ISEE calculation canceled.",
            'it': "❌ Calcolo ISEE annullato."
        }
        context.user_data.clear()
        await update.message.reply_text(
            text=sanitize_markdown(messages[lang]),
            parse_mode='MarkdownV2',
            reply_markup=get_main_menu_keyboard(lang)
        )
        return MAIN_MENU
