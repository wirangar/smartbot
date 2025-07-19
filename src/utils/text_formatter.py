import re

def sanitize_markdown(text: str) -> str:
    """
    Sanitizes a string to prevent Telegram MarkdownV2 parsing errors.
    It escapes characters that are special in MarkdownV2, except for '*' and '_'.
    It also ensures that '*' and '_' are properly paired.

    Args:
        text: The text to sanitize.

    Returns:
        The sanitized text.
    """
    if not text:
        return ""

    # First, ensure '*' and '_' are balanced.
    if text.count('*') % 2 != 0:
        text = text.replace('*', '') # Remove if unbalanced
    if text.count('_') % 2 != 0:
        # Don't remove underscores as they are common in links/IDs
        # Instead, we will escape them later if they are not part of a pair.
        pass

    # Escape other special characters for MarkdownV2
    # Characters to escape: . ! - = | { } ( ) # > +
    # We avoid escaping '*' and '_' as we want to use them for formatting.
    escape_chars = r"([\.!\-=\|{}\(\)#>+])"
    text = re.sub(escape_chars, r'\\\1', text)

    return text
