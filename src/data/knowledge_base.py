import json
import logging
import re
from pathlib import Path
from typing import Tuple, List, Dict

from src.config import logger

# مسیر فایل JSON پایگاه دانش
BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_FILE = BASE_DIR / 'data' / 'knowledge_base_v2.json'
knowledge_base: Dict = {}

def load_knowledge_base() -> None:
    """بارگذاری پایگاه دانش از فایل JSON."""
    global knowledge_base
    try:
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
        logger.info(f"Knowledge base '{KNOWLEDGE_FILE.name}' loaded successfully.")
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
        return "No content found.", None

    category_key, item_id = path_parts[0], path_parts[1]
    category = kb.get(category_key, [])
    if not isinstance(category, list):
        logger.warning(f"Invalid category format: {category_key}")
        return f"Category '{category_key}' is invalid.", None

    target_item = next((item for item in category if item.get('id') == item_id), None)
    if not target_item:
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
    kb = get_knowledge_base()
    results = []
    query = query.lower().strip()

    for category_name, items in kb.items():
        if not isinstance(items, list):
            logger.warning(f"Invalid data format for category '{category_name}'")
            continue
        for item in items:
            if not isinstance(item, dict):
                logger.warning(f"Invalid item format in category '{category_name}'")
                continue
            title = item.get('title', {}).get(lang, item.get('title', {}).get('en', '')).lower()
            description = item.get('description', {}).get(lang, item.get('description', {}).get('en', '')).lower()
            subsections = item.get('subsections', [])
            # جستجو در عنوان و توضیحات
            if query in title or query in description:
                results.append({
                    "title": item.get('title', {}).get(lang, item.get('title', {}).get('en', 'No Title')),
                    "callback": f"menu:{category_name}:{item.get('id', '')}"
                })
            # جستجو در زیربخش‌ها
            for subsection in subsections:
                sub_title = subsection.get('title', {}).get(lang, subsection.get('title', {}).get('en', '')).lower()
                sub_content = subsection.get('content', {}).get(lang, subsection.get('content', {}).get('en', [])).lower()
                if query in sub_title or (isinstance(sub_content, str) and query in sub_content):
                    results.append({
                        "title": item.get('title', {}).get(lang, item.get('title', {}).get('en', 'No Title')),
                        "callback": f"menu:{category_name}:{item.get('id', '')}"
                    })
                    break

    # حذف موارد تکراری
    seen = set()
    unique_results = []
    for result in results:
        if result['callback'] not in seen:
            seen.add(result['callback'])
            unique_results.append(result)

    return unique_results

# بارگذاری اولیه پایگاه دانش
load_knowledge_base()
