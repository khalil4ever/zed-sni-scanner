from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    """
    Returns the main navigation keyboard.
    """
    keyboard = [
        [InlineKeyboardButton(text="🧪 Test Hostname", callback_data="test")],
        [InlineKeyboardButton(text="📊 Bot Status", callback_data="status")],
        [InlineKeyboardButton(text="🇿🇲 Scan Network", callback_data="network")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def network_selection_keyboard():
    """
    Returns an inline keyboard with Zambian network options for the SNI scanner.
    """
    keyboard = [
        [InlineKeyboardButton(text="🇿🇲 MTN Zambia", callback_data="scan_mtn")],
        [InlineKeyboardButton(text="🇿🇲 Airtel Zambia", callback_data="scan_airtel")],
        [InlineKeyboardButton(text="🇿🇲 Zamtel Zambia", callback_data="scan_zamtel")],
        [InlineKeyboardButton(text="⌨️ Type Custom Hostname", callback_data="scan_custom")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
