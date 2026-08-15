from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def network_selection_keyboard():
    """
    Returns an inline keyboard with Zambian network options for the SNI scanner.
    """
    keyboard = [
        [InlineKeyboardButton("🇿🇲 MTN Zambia", callback_data="scan_mtn")],
        [InlineKeyboardButton("🇿🇲 Airtel Zambia", callback_data="scan_airtel")],
        [InlineKeyboardButton("🇿🇲 Zamtel Zambia", callback_data="scan_zamtel")],
        [InlineKeyboardButton("⌨️ Type Custom Hostname", callback_data="scan_custom")]
    ]
    return InlineKeyboardMarkup(keyboard)
