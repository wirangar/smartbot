import logging
from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
from src.config import logger
from src.utils.text_formatter import sanitize_markdown
from src.utils.paginator import Paginator
from src.utils.keyboard_builder import get_main_menu_keyboard
from src.database import get_db_cursor

class SearchEngine:
    def __init__(self, json_data: dict, db_manager, paginator: Paginator):
        self.json_data = json_data if json_data else {}
        self.db = db_manager
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

        if not self.json_data:
            messages = {
                'fa': "❌ پایگاه داده دانش در دسترس نیست.",
                'en': "❌ Knowledge base is not available.",
                'it': "❌ La base di conoscenza non è disponibile."
            }
            await update.message.reply_text(
                sanitize_markdown(messages[lang]),
                parse_mode='MarkdownV2',
                reply_markup=get_main_menu_keyboard(lang)
            )
            context.user_data['awaiting_search_query'] = False
            return MAIN_MENU

        results = []
        try:
            for section in self.json_data.values():
                for item in section:
                    title = item.get(lang, {}).get('title', item.get('title', '')).lower()
                    description = item.get(lang, {}).get('description', item.get('description', '')).lower()
                    content = item.get(lang, {}).get('content', item.get('content', []))
                    details = item.get(lang, {}).get('details', item.get('details', []))

                    if query in title:
                        results.append(f"*{sanitize_markdown(title)}*\n{sanitize_markdown(description)}")
                    if isinstance(content, list):
                        results.extend([sanitize_markdown(line) for line in content if query in line.lower()])
                    elif isinstance(content, str) and query in content.lower():
                        results.append(sanitize_markdown(content))
                    if isinstance(details, list):
                        results.extend([sanitize_markdown(detail) for detail in details if query in detail.lower()])
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

        if results:
            self.paginator.create_session(user_id, results, 'text')
            page_data = self.paginator._prepare_page({
                'content': results,
                'type': 'text',
                'current_page': 0,
                'total_pages': len(results)
            })
            await update.message.reply_text(
                sanitize_markdown(f"{page_data['content']}\n\nصفحه {page_data['page_num']} از {page_data['total_pages']}" if lang == 'fa' else
                                f"{page_data['content']}\n\nPage {page_data['page_num']} of {page_data['total_pages']}" if lang == 'en' else
                                f"{page_data['content']}\n\nPagina {page_data['page_num']} di {page_data['total_pages']}"),
                parse_mode='MarkdownV2',
                reply_markup=self.paginator.get_pagination_markup(page_data, lang)
            )
        else:
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
