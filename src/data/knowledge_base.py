import json
import logging
import re
from pathlib import Path
from typing import Tuple, List, Dict

from src.config import logger

# مسیر فایل JSON پایگاه دانش
BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_FILE = BASE_DIR / 'src' / 'data' / 'knowledge_base_v2.json'
knowledge_base: Dict = {}
inverted_index: Dict[str, Dict[str, List[str]]] = {}

def build_inverted_index():
    """Build an inverted index for the knowledge base."""
    global inverted_index
    kb = get_knowledge_base()
    for lang in ['fa', 'en', 'it']:
        inverted_index[lang] = {}
        for category_name, items in kb.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue

                # Index title
                title = item.get('title', {}).get(lang, '').lower()
                for word in re.findall(r'\w+', title):
                    if word not in inverted_index[lang]:
                        inverted_index[lang][word] = []
                    inverted_index[lang][word].append(f"menu:{category_name}:{item.get('id', '')}")

                # Index description
                description = item.get('description', {}).get(lang, '').lower()
                for word in re.findall(r'\w+', description):
                    if word not in inverted_index[lang]:
                        inverted_index[lang][word] = []
                    inverted_index[lang][word].append(f"menu:{category_name}:{item.get('id', '')}")

                # Index subsections
                for subsection in item.get('subsections', []):
                    sub_title = subsection.get('title', {}).get(lang, '').lower()
                    for word in re.findall(r'\w+', sub_title):
                        if word not in inverted_index[lang]:
                            inverted_index[lang][word] = []
                        inverted_index[lang][word].append(f"menu:{category_name}:{item.get('id', '')}")

                    sub_content = subsection.get('content', {}).get(lang, [])
                    if isinstance(sub_content, str):
                        for word in re.findall(r'\w+', sub_content):
                            if word not in inverted_index[lang]:
                                inverted_index[lang][word] = []
                            inverted_index[lang][word].append(f"menu:{category_name}:{item.get('id', '')}")
                    elif isinstance(sub_content, list):
                        for line in sub_content:
                            for word in re.findall(r'\w+', line):
                                if word not in inverted_index[lang]:
                                    inverted_index[lang][word] = []
                                inverted_index[lang][word].append(f"menu:{category_name}:{item.get('id', '')}")

def load_knowledge_base() -> None:
    """بارگذاری پایگاه دانش از فایل JSON."""
    global knowledge_base
    try:
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
        logger.info(f"Knowledge base '{KNOWLEDGE_FILE.name}' loaded successfully.")
        build_inverted_index()
        logger.info("Inverted index built successfully.")
    except FileNotFoundError:
        logger.error(f"Knowledge base file '{KNOWLEDGE_FILE.name}' not found.")
        # ایجاد فایل JSON خالی به‌عنوان پیش‌فرض
        knowledge_base = {"categories": []}
        with open(KNOWLEDGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(knowledge_base, f, ensure_ascii=False, indent=2)
        logger.info(f"Created an empty knowledge base at '{KNOWLEDGE_FILE.name}'.")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from '{KNOWLEDGE_FILE.name}': {e}")
        raise Exception("Invalid knowledge base format. Please check the JSON file.")

def get_knowledge_base() -> Dict:
    """بازگرداندن پایگاه دانش و بارگذاری آن در صورت خالی بودن."""
    if not knowledge_base:
        load_knowledge_base()
    return knowledge_base

def get_content_by_path(path_parts: List[str], lang: str = 'fa') -> Tuple[str, str | None]:
    """
    بازیابی و فرمت‌بندی محتوا از پایگاه دانش بر اساس مسیر.
    خروجی: (محتوای فرمت‌شده, مسیر فایل برای ارسال)
    """
    kb = get_knowledge_base()
    if not path_parts or len(path_parts) < 2:
        logger.error(f"Invalid path_parts provided: {path_parts}")
        return "Invalid request. Please try again.", None

    category_key, item_id = path_parts[0], path_parts[1]
    category = kb.get(category_key)
    if not category or not isinstance(category, list):
        logger.warning(f"Invalid or missing category: {category_key}")
        return f"Category '{category_key}' not found or is invalid.", None

    target_item = next((item for item in category if item.get('id') == item_id), None)
    if not target_item:
        logger.warning(f"Item with ID '{item_id}' not found in category '{category_key}'.")
        return f"Item with ID '{item_id}' not found.", None

    output_parts = []
    file_to_send = None

    # بازیابی عنوان و توضیحات با بازگشت به زبان انگلیسی در صورت عدم وجود زبان کاربر
    title = target_item.get('title', {}).get(lang) or target_item.get('title', {}).get('en', '')
    description = target_item.get('description', {}).get(lang) or target_item.get('description', {}).get('en', '')

    if title:
        output_parts.append(f"*{title}*")
    if description:
        output_parts.append(f"_{description}_")

    # زیربخش‌ها
    if 'subsections' in target_item:
        for subsection in target_item['subsections']:
            sub_title = subsection.get('title', {}).get(lang) or subsection.get('title', {}).get('en', '')
            if sub_title:
                output_parts.append(f"\n*{sub_title}*")

            sub_content = subsection.get('content', {}).get(lang, [])
            if isinstance(sub_content, list):
                for line in sub_content:
                    match = re.search(r'\(([^)]+\.(?:pdf|jpg|jpeg|png))\)', line, re.IGNORECASE)
                    if match:
                        file_name = match.group(1)
                        extension = file_name.split('.')[-1].lower()
                        if extension in ['jpg', 'jpeg', 'png']:
                            file_to_send = str(BASE_DIR / "assets" / "images" / file_name)
                        elif extension == 'pdf':
                            file_to_send = str(BASE_DIR / "assets" / "pdf" / file_name)
                    output_parts.append(line)
            else:
                output_parts.append(sub_content)

    formatted_content = "\n\n".join(output_parts)
    return formatted_content, file_to_send

def search_knowledge_base(query: str, lang: str = 'fa') -> List[Dict]:
    """جستجوی پیشرفته در پایگاه دانش و بازگرداندن موارد منطبق."""
    if not inverted_index:
        build_inverted_index()

    query_words = re.findall(r'\w+', query.lower().strip())
    if not query_words:
        return []

    # Get all documents that contain any of the query words
    result_callbacks = set()
    for word in query_words:
        if word in inverted_index.get(lang, {}):
            for callback in inverted_index[lang][word]:
                result_callbacks.add(callback)

    # Rank results by the number of matching words
    ranked_results = {}
    for callback in result_callbacks:
        rank = 0
        category_key, item_id = callback.replace("menu:", "").split(":")
        item = next((i for i in knowledge_base.get(category_key, []) if i.get('id') == item_id), None)
        if item:
            text_to_search = (item.get('title', {}).get(lang, '') + " " +
                              item.get('description', {}).get(lang, ''))
            for sub in item.get('subsections', []):
                text_to_search += " " + sub.get('title', {}).get(lang, '')
                content = sub.get('content', {}).get(lang, [])
                if isinstance(content, str):
                    text_to_search += " " + content
                elif isinstance(content, list):
                    text_to_search += " ".join(content)

            for word in query_words:
                if word in text_to_search.lower():
                    rank += 1

            ranked_results[callback] = {
                "rank": rank,
                "title": item.get('title', {}).get(lang, item.get('title', {}).get('en', 'No Title')),
                "callback": callback
            }

    # Sort results by rank
    sorted_results = sorted(ranked_results.values(), key=lambda x: x['rank'], reverse=True)

    # Remove rank from the final result
    return [{ "title": res["title"], "callback": res["callback"]} for res in sorted_results]

# بارگذاری اولیه پایگاه دانش
load_knowledge_base()
