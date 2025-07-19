# Centralized dictionary for multilingual messages
# Using emojis to make the bot more engaging

class Emoji:
    ISEE = "📊"
    ERROR = "❌"
    SUCCESS = "✅"
    PROMPT = "💬"
    INFO = "ℹ️"

MESSAGES = {
    'fa': {
        "start_isee": f"{Emoji.ISEE} به بخش محاسبه ISEE خوش آمدید. لطفاً درآمد سالیانه خانواده خود را به یورو وارد کنید:",
        "ask_property": f"{Emoji.PROMPT} لطفاً ارزش کل املاک خانواده (به یورو) را وارد کنید (اگر اجاره‌نشین هستید، 0 وارد کنید):",
        "ask_family": f"{Emoji.PROMPT} لطفاً تعداد اعضای خانواده را وارد کنید (حداقل 1):",
        "invalid_number": f"{Emoji.ERROR} ورودی نامعتبر است. لطفاً یک عدد صحیح و مثبت وارد کنید.",
        "invalid_family": f"{Emoji.ERROR} تعداد اعضای خانواده باید حداقل 1 نفر باشد.",
        "confirm_isee": (
            f"{Emoji.INFO} *اطلاعات وارد شده:*\n"
            "💰 درآمد سالیانه: €{income:,.2f}\n"
            "🏡 ارزش املاک: €{property:,.2f}\n"
            "👨‍👩‍👧 تعداد اعضای خانواده: {family}\n\n"
            "📊 *ISEE محاسبه‌شده:* €{isee_value:,.2f}\n\n"
            "آیا اطلاعات را تأیید می‌کنید؟"
        ),
        "isee_saved": f"{Emoji.SUCCESS} عدد ISEE شما با موفقیت ثبت شد.",
        "isee_cancelled": f"{Emoji.ERROR} محاسبه ISEE لغو شد.",
        "confirm_prompt": "لطفاً با استفاده از دکمه‌ها تأیید کنید.",
        "yes": "✅ بله",
        "no": "❌ خیر",
    },
    'en': {
        "start_isee": f"{Emoji.ISEE} Welcome to the ISEE calculator. Please enter your family's annual income in EUR:",
        "ask_property": f"{Emoji.PROMPT} Please enter the total value of family properties in EUR (enter 0 if you rent):",
        "ask_family": f"{Emoji.PROMPT} Please enter the number of family members (minimum 1):",
        "invalid_number": f"{Emoji.ERROR} Invalid input. Please enter a valid positive number.",
        "invalid_family": f"{Emoji.ERROR} The number of family members must be at least 1.",
        "confirm_isee": (
            f"{Emoji.INFO} *Entered Information:*\n"
            "💰 Annual Income: €{income:,.2f}\n"
            "🏡 Property Value: €{property:,.2f}\n"
            "👨‍👩‍👧 Family Members: {family}\n\n"
            "📊 *Calculated ISEE:* €{isee_value:,.2f}\n\n"
            "Do you confirm this information?"
        ),
        "isee_saved": f"{Emoji.SUCCESS} Your ISEE value has been successfully saved.",
        "isee_cancelled": f"{Emoji.ERROR} ISEE calculation has been cancelled.",
        "confirm_prompt": "Please confirm using the buttons.",
        "yes": "✅ Yes",
        "no": "❌ No",
    },
    'it': {
        "start_isee": f"{Emoji.ISEE} Benvenuti nel calcolatore ISEE. Inserisci il reddito annuo della tua famiglia in EUR:",
        "ask_property": f"{Emoji.PROMPT} Inserisci il valore totale delle proprietà familiari in EUR (inserisci 0 se sei in affitto):",
        "ask_family": f"{Emoji.PROMPT} Inserisci il numero di membri della famiglia (minimo 1):",
        "invalid_number": f"{Emoji.ERROR} Inserimento non valido. Inserisci un numero positivo valido.",
        "invalid_family": f"{Emoji.ERROR} Il numero di membri della famiglia deve essere almeno 1.",
        "confirm_isee": (
            f"{Emoji.INFO} *Informazioni Inserite:*\n"
            "💰 Reddito Annuo: €{income:,.2f}\n"
            "🏡 Valore Proprietà: €{property:,.2f}\n"
            "👨‍👩‍👧 Membri Famiglia: {family}\n\n"
            "📊 *ISEE Calcolato:* €{isee_value:,.2f}\n\n"
            "Confermi queste informazioni?"
        ),
        "isee_saved": f"{Emoji.SUCCESS} Il tuo valore ISEE è stato salvato con successo.",
        "isee_cancelled": f"{Emoji.ERROR} Il calcolo dell'ISEE è stato annullato.",
        "confirm_prompt": "Si prega di confermare utilizzando i pulsanti.",
        "yes": "✅ Sì",
        "no": "❌ No",
    }
}

def get_message(key: str, lang: str, **kwargs) -> str:
    """
    Retrieves a formatted message from the MESSAGES dictionary.
    """
    lang = lang if lang in MESSAGES else 'en' # Default to English if lang is not found
    message = MESSAGES.get(lang, {}).get(key, "Message not found.")

    if kwargs:
        return message.format(**kwargs)
    return message
