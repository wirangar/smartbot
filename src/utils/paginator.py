import logging
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.config import logger
from src.database import get_redis_client
from src.utils.text_formatter import sanitize_markdown
from src.utils.keyboard_builder import get_main_menu_keyboard

class Paginator:
    def __init__(self):
        self.redis = get_redis_client()
        self.expire_time = 3600  # 1 ساعت

    def _get_key(self, user_id: int) -> str:
        """ایجاد کلید منحصربه‌فرد برای کاربر در Redis."""
        return f"pagination:{user_id}"

    def create_session(self, user_id: int, content: List[Any], content_type: str):
        """ایجاد سشن صفحه‌بندی در Redis."""
        try:
            session_data = {
                'content': content,
                'type': content_type,
                'current_page': 0,
                'total_pages': len(content),
                'created_at': datetime.now().isoformat()
            }
            if self.redis:
                self.redis.setex(self._get_key(user_id), self.expire_time, json.dumps(session_data))
                logger.info(f"Pagination session created for user {user_id}")
            else:
                logger.warning("Redis not available, pagination session not created.")
        except Exception as e:
            logger.error(f"Error creating pagination session for user {user_id}: {e}")

    def get_next_page(self, user_id: int) -> Optional[Dict]:
        """دریافت صفحه بعدی."""
        try:
            if not self.redis:
                logger.warning("Redis not available for pagination.")
                return None
            data = self.redis.get(self._get_key(user_id))
            if not data:
                logger.info(f"No pagination session found for user {user_id}")
                return None
            session = json.loads(data)
            session['current_page'] += 1
            if session['current_page'] >= session['total_pages']:
                logger.info(f"Reached last page for user {user_id}")
                return None
            self.redis.setex(self._get_key(user_id), self.expire_time, json.dumps(session))
            return self._prepare_page(session)
        except Exception as e:
            logger.error(f"Error getting next page for user {user_id}: {e}")
            return None

    def get_prev_page(self, user_id: int) -> Optional[Dict]:
        """دریافت صفحه قبلی."""
        try:
            if not self.redis:
                logger.warning("Redis not available for pagination.")
                return None
            data = self.redis.get(self._get_key(user_id))
            if not data:
                logger.info(f"No pagination session found for user {user_id}")
                return None
            session = json.loads(data)
            session['current_page'] -= 1
            if session['current_page'] < 0:
                logger.info(f"Reached first page for user {user_id}")
                return None
            self.redis.setex(self._get_key(user_id), self.expire_time, json.dumps(session))
            return self._prepare_page(session)
        except Exception as e:
            logger.error(f"Error getting previous page for user {user_id}: {e}")
            return None

    def _prepare_page(self, session: Dict) -> Dict:
        """آماده‌سازی داده‌های صفحه."""
        return {
            'content': session['content'][session['current_page']],
            'page_num': session['current_page'] + 1,
            'total_pages': session['total_pages'],
            'type': session['type']
        }

    def get_pagination_markup(self, page_data: Dict, lang: str = 'fa') -> InlineKeyboardMarkup:
        """ایجاد کیبورد صفحه‌بندی."""
        buttons = []
        if page_data['page_num'] > 1:
            buttons.append(InlineKeyboardButton(
                "⬅️ قبلی" if lang == 'fa' else "⬅️ Previous" if lang == 'en' else "⬅️ Precedente",
                callback_data="pagination:prev"
            ))
        if page_data['page_num'] < page_data['total_pages']:
            buttons.append(InlineKeyboardButton(
                "بعدی ➡️" if lang == 'fa' else "Next ➡️" if lang == 'en' else "Successivo ➡️",
                callback_data="pagination:next"
            ))
        buttons.append(InlineKeyboardButton(
            "🔙 بازگشت" if lang == 'fa' else "🔙 Back" if lang == 'en' else "🔙 Indietro",
            callback_data="menu:main_menu"
        ))
        return InlineKeyboardMarkup([buttons])
