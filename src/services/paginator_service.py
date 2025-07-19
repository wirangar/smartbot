import json
import logging
from src.database import get_redis_client
from src.config import logger

class PaginatorService:
    def __init__(self):
        self.redis = get_redis_client()
        if not self.redis:
            logger.warning("Redis is not available. Paginator service will be disabled.")

    def create_session(self, user_id: int, content: list):
        """Creates a new pagination session for a user."""
        if not self.redis: return
        session_key = f"pagination:{user_id}"
        session_data = {
            "content": content,
            "current_page": 0,
            "total_pages": len(content)
        }
        # Store the session in Redis for 1 hour (3600 seconds)
        self.redis.set(session_key, json.dumps(session_data), ex=3600)
        logger.info(f"Pagination session created for user {user_id} with {len(content)} items.")

    def _get_session(self, user_id: int) -> dict | None:
        """Retrieves a pagination session from Redis."""
        if not self.redis: return None
        session_key = f"pagination:{user_id}"
        session_data = self.redis.get(session_key)
        return json.loads(session_data) if session_data else None

    def _save_session(self, user_id: int, session_data: dict):
        """Saves the updated session back to Redis."""
        if not self.redis: return
        session_key = f"pagination:{user_id}"
        self.redis.set(session_key, json.dumps(session_data), ex=3600)

    def _prepare_page_data(self, session_data: dict) -> dict:
        """Prepares the data for the current page."""
        current_page = session_data['current_page']
        total_pages = session_data['total_pages']

        if not session_data['content'] or current_page >= total_pages:
            return None

        content_item = session_data['content'][current_page]

        return {
            'content': content_item,
            'page_num': current_page + 1,
            'total_pages': total_pages
        }

    def get_current_page(self, user_id: int) -> dict | None:
        """Gets the current page for a user."""
        session_data = self._get_session(user_id)
        return self._prepare_page_data(session_data) if session_data else None

    def get_next_page(self, user_id: int) -> dict | None:
        """Moves to the next page and returns its content."""
        session_data = self._get_session(user_id)
        if not session_data or session_data['current_page'] + 1 >= session_data['total_pages']:
            return None # No next page

        session_data['current_page'] += 1
        self._save_session(user_id, session_data)
        return self._prepare_page_data(session_data)

    def get_prev_page(self, user_id: int) -> dict | None:
        """Moves to the previous page and returns its content."""
        session_data = self._get_session(user_id)
        if not session_data or session_data['current_page'] <= 0:
            return None # No previous page

        session_data['current_page'] -= 1
        self._save_session(user_id, session_data)
        return self._prepare_page_data(session_data)
