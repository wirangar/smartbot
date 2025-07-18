import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

KNOWLEDGE_FILE = Path(__file__).parent / 'knowledge.json'
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

def get_json_content_by_path(path_parts: list) -> str:
    kb = get_knowledge_base()
    current_level = kb
    content = ""
    try:
        for i, part in enumerate(path_parts):
            if isinstance(current_level, dict):
                current_level = current_level.get(part)
            elif isinstance(current_level, list):
                found_item = next((item for item in current_level if item.get('title') == part or (item.get('fa') and item['fa'].get('title') == part)), None)
                current_level = found_item

            if not current_level:
                return ""

            if i == len(path_parts) - 1:
                # This logic is complex and might need refactoring, but for now, it's a direct move.
                if 'fa' in current_level:
                    if 'content' in current_level['fa']:
                        content = current_level['fa']['content']
                    elif 'description' in current_level['fa']:
                        content = current_level['fa']['description']
                        if current_level['fa'].get('details'):
                            content += "\\n" + "\\n".join(current_level['fa']['details'])
                        if current_level['fa'].get('steps'):
                            steps_content = [f"{step.get('title', '')}: {step.get('content', '') or ' / '.join(step.get('items', []))}" for step in current_level['fa']['steps']]
                            content += "\\nمراحل:\\n" + "\\n".join(steps_content)
                elif 'content' in current_level:
                    content = "\\n".join(current_level['content']) if isinstance(current_level['content'], list) else current_level['content']
                elif 'points' in current_level:
                    content = "\\n".join(current_level['points'])
        return content
    except Exception as e:
        logger.error(f"Error navigating JSON path {path_parts}: {e}")
        return ""

# Load on module import
load_knowledge_base()
