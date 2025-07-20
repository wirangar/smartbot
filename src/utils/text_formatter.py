import re

def sanitize_markdown(text: str) -> str:
    """
    Escapes characters for Telegram's MarkdownV2 parser.
    This is a more robust version to prevent parsing errors.
    """
    if not text:
        return ""

    # Characters that need to be escaped in MarkdownV2
    escape_chars = r'\_*[]()~`>#+-=|{}.!'

    # Create a regex pattern to find any of these characters
    # and escape them with a preceding backslash
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
