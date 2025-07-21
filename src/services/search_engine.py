import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, filters, ContextTypes
from src.config import logger
from src.utils.text_formatter import sanitize_markdown
from src.utils.paginator import Paginator
from src.utils.keyboard_builder import get_main_menu_keyboard
from src.database import get_db_cursor
from src.data.knowledge_base import search_knowledge_base, get_content_by_path

class SearchEngine:
    def __init__(self, paginator: Paginator):
        self.paginator = paginator

    def get_handler(self):
        """بازگشت handler برای جستجو."""
        return MessageHandler(filters.TEXT & ~filters.COMMAND, self.search)

    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """مدیریت جستجوی کاربر."""
        from src.handlers.user_manager import MAIN_MENU
        if not context.user_data.get('awaiting_search_query', False):
            logger.info(f"User {update.effective_user.id} sent text without search context.")
            return MAIN_MENU
        query = update.message.text.lower()
        user_id = update.effective_user.id
        with get_db_cursor() as cur:
            cur.execute("SELECT language FROM users WHERE telegram_id = %s", (user_id,))
            result = cur.fetchone()
            lang = result[0] if result else 'fa'

        try:
            # استفاده از search_knowledge_base برای جستجو
            results = search_knowledge_base(query, lang)
            if not results:
                messages = {
                    'fa': "❌ نتیجه‌ای یافت نشد.",
                    'en': "❌ No results found.",
                    'it': "❌ Nessun risultato trovato."
                }
                await update.message.reply_text(
                    sanitize_markdown(messages[lang]),
                    parse_mode='MarkdownV2',
                    reply_markup=get_main_menu_keyboard(lang)
                )
                context.user_data['awaiting_search_query'] = False
                return MAIN_MENU

            # آماده‌سازی محتوا برای صفحه‌بندی
            formatted_results = []
            for result in results:
                callback = result['callback'].replace("menu:", "")
                content, file_path = get_content_by_path(callback.split(":"), lang)
                formatted_results.append({
                    "content": content,
                    "file_path": file_path,
                    "callback": result['callback']
                })

            # ذخیره نتایج در Paginator
            self.paginator.create_session(user_id, formatted_results, 'search')
            page_data = self.paginator._prepare_page({
                'content': formatted_results,
                'type': 'search',
                'current_page': 0,
                'total_pages': len(formatted_results)
            })

            # ارسال محتوا و فایل (اگه وجود داره)
            await update.message.reply_text(
                sanitize_markdown(f"{page_data['content']['content']}\n\nصفحه {page_data['page_num']} از {page_data['total_pages']}" if lang == 'fa' else
                                f"{page_data['content']['content']}\n\nPage {page_data['page_num']} of {page_data['total_pages']}" if lang == 'en' else
                                f"{page_data['content']['content']}\n\nPagina {page_data['page_num']} di {page_data['total_pages']}"),
                parse_mode='MarkdownV2',
                reply_markup=self.paginator.get_pagination_markup(page_data, lang)
            )

            # ارسال فایل اگه وجود داشته باشه
            if page_data['content']['file_path']:
                try:
                    with open(page_data['content']['file_path'], 'rb') as f:
                        if page_data['content']['file_path'].endswith(('.jpg', '.jpeg', '.png')):
                            await update.message.reply_photo(photo=f)
                        elif page_data['content']['file_path'].endswith('.pdf'):
                            await update.message.reply_document(document=f)
                except Exception as e:
                    logger.error(f"Error sending file {page_data['content']['file_path']} for user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error searching knowledge base for user {user_id}: {e}")
            messages = {
                'fa': "❌ خطایی در جستجو رخ داد. لطفاً دوباره امتحان کنید.",
                'en': "❌ An error occurred during search. Please try again.",
                'it': "❌ Si è verificato un errore durante la ricerca. Riprova."
            }
            await update.message.reply_text(
                sanitize_markdown(messages[lang]),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )

        context.user_data['awaiting_search_query'] = False
        return MAIN_MENU
