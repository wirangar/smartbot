import logging
from src.config import logger
from src.data.knowledge_base import get_knowledge_base

class SearchService:
    def __init__(self):
        self.kb = get_knowledge_base()
        if not self.kb:
            logger.warning("SearchService initialized with an empty knowledge base.")

    def search(self, query: str, lang: str = 'fa') -> list:
        """
        Performs a simple case-insensitive search across titles and descriptions.
        """
        if not self.kb or not query:
            return []

        query_lower = query.lower()
        results = []

        for category_name, items in self.kb.items():
            for item in items:
                title = item.get('title', {}).get(lang, '').lower()
                description = item.get('description', {}).get(lang, '').lower()

                if query_lower in title or query_lower in description:
                    # Create a brief snippet for the result
                    snippet = description[:100] + '...' if description else ""

                    results.append({
                        "title": item.get('title', {}).get(lang, 'No Title'),
                        "snippet": snippet,
                        "callback": f"menu:{category_name}:{item.get('id')}"
                    })

        logger.info(f"Search for query '{query}' yielded {len(results)} results.")
        return results
