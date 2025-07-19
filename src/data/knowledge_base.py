import json
import logging
import re
from pathlib import Path

from src.config import logger

KNOWLEDGE_FILE = Path(__file__).parent / 'knowledge_base_v2.json'
knowledge_base = {}

def load_knowledge_base():
    """Loads the knowledge base from the JSON file."""
    global knowledge_base
    try:
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
        logger.info(f"Knowledge base '{KNOWLEDGE_FILE.name}' loaded successfully.")
    except FileNotFoundError:
        logger.error(f"Knowledge base file '{KNOWLEDGE_FILE.name}' not found.")
        knowledge_base = {}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from '{KNOWLEDGE_FILE.name}': {e}")
        knowledge_base = {}

def get_knowledge_base():
    """Returns the loaded knowledge base, loading it if it's empty."""
    if not knowledge_base:
        load_knowledge_base()
    return knowledge_base

def get_content_by_path(path_parts: list, lang: str = 'fa') -> (str, str):
    """
    Retrieves and formats content from the knowledge base based on a path.
    Returns a tuple of (formatted_content, file_to_send_path).
    """
    kb = get_knowledge_base()
    if not path_parts or len(path_parts) < 2:
        return "محتوایی یافت نشد.", None

    category_key, item_id = path_parts[0], path_parts[1]

    category = kb.get(category_key, [])
    target_item = next((item for item in category if item.get('id') == item_id), None)

    if not target_item:
        return f"موردی با شناسه '{item_id}' یافت نشد.", None

    output_parts = []
    file_to_send = None

    # Title, Description, and File
    title = target_item.get('title', {}).get(lang, '')
    description = target_item.get('description', {}).get(lang, '')

    if title:
        output_parts.append(f"*{title}*")
    if description:
        output_parts.append(f"_{description}_")

    # Subsections
    if 'subsections' in target_item:
        for subsection in target_item['subsections']:
            sub_title = subsection.get('title', {}).get(lang, '')
            if sub_title:
                output_parts.append(f"\n*{sub_title}*")

            sub_content = subsection.get('content', {}).get(lang, [])
            if isinstance(sub_content, list):
                # Check for file references in content
                for line in sub_content:
                    # Improved file reference extraction
                    match = re.search(r'\(([^)]+\.(?:pdf|jpg|jpeg|png))\)', line, re.IGNORECASE)
                    if match:
                        file_name = match.group(1)
                        # Determine subdirectory based on extension
                        extension = file_name.split('.')[-1].lower()
                        if extension in ['jpg', 'jpeg', 'png']:
                            file_to_send = f"assets/images/{file_name}"
                        elif extension == 'pdf':
                            file_to_send = f"assets/pdf/{file_name}"
                        # Add more types if needed (video, audio)
                    output_parts.append(line)
            else:
                output_parts.append(sub_content)

    formatted_content = "\n\n".join(output_parts)
    return formatted_content, file_to_send

def search_knowledge_base(query: str, lang: str = 'fa') -> list:
    """Searches the knowledge base for a query and returns matching items."""
    kb = get_knowledge_base()
    results = []
    for category_name, items in kb.items():
        for item in items:
            title = item.get('title', {}).get(lang, '').lower()
            description = item.get('description', {}).get(lang, '').lower()
            if query.lower() in title or query.lower() in description:
                results.append({
                    "title": item.get('title', {}).get(lang, 'No Title'),
                    "callback": f"menu:{category_name}:{item.get('id')}"
                })
    return results

# Load the knowledge base on module import
load_knowledge_base()
