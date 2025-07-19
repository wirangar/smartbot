import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

KNOWLEDGE_FILE = Path(__file__).parent / 'knowledge_base_v2.json'
knowledge_base = {}

def load_knowledge_base():
    global knowledge_base
    try:
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
        logger.info(f"Knowledge base '{KNOWLEDGE_FILE.name}' loaded successfully.")
    except FileNotFoundError:
        logger.error(f"Knowledge base file '{KNOWLEDGE_FILE.name}' not found.")
        knowledge_base = {}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from '{KNOWLEDGE_FILE.name}'.")
        knowledge_base = {}

def get_knowledge_base():
    if not knowledge_base:
        load_knowledge_base()
    return knowledge_base

def get_json_content_by_path(path_parts: list, lang: str = 'fa') -> str:
    kb = get_knowledge_base()
    if not path_parts:
        return ""

    # Navigate to the correct category
    category_key = path_parts[0]
    if category_key not in kb:
        return ""

    current_list = kb[category_key]

    # Find the specific item by ID
    item_id = path_parts[1] if len(path_parts) > 1 else None
    if not item_id:
        # If no item ID is provided, maybe return category description? For now, empty.
        return ""

    target_item = next((item for item in current_list if item.get('id') == item_id), None)

    if not target_item:
        return f"موردی با شناسه '{item_id}' یافت نشد."

    # Build the content string
    output_parts = []

    # Title
    if 'title' in target_item and lang in target_item['title']:
        output_parts.append(f"*{target_item['title'][lang]}*")

    # Description
    if 'description' in target_item and lang in target_item['description']:
        output_parts.append(f"_{target_item['description'][lang]}_")

    # Main content (if it's a list of strings)
    if 'content' in target_item and isinstance(target_item['content'], dict) and lang in target_item['content']:
        if isinstance(target_item['content'][lang], list):
            output_parts.extend(target_item['content'][lang])
        else:
            output_parts.append(target_item['content'][lang])

    # Subsections
    if 'subsections' in target_item:
        for subsection in target_item['subsections']:
            if 'title' in subsection and lang in subsection['title']:
                output_parts.append(f"\n*{subsection['title'][lang]}*")
            if 'content' in subsection and lang in subsection['content']:
                if isinstance(subsection['content'][lang], list):
                    output_parts.extend(subsection['content'][lang])
                else:
                    output_parts.append(subsection['content'][lang])

    return "\n\n".join(output_parts)

# Load on module import
load_knowledge_base()
