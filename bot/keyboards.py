from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Choose Network",
                    callback_data="network"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧪 Test Hostname",
                    callback_data="test"
                ),
                InlineKeyboardButton(
                    text="📊 Status",
                    callback_data="status"
                )
            ],
        ]
    )


def network_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇿🇲 MTN Zambia",
                    callback_data="net:MTN Zambia"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇿🇲 Airtel Zambia",
                    callback_data="net:Airtel Zambia"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇿🇲 Zamtel",
                    callback_data="net:Zamtel"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇿🇲 ZedMobile",
                    callback_data="net:ZedMobile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data="status"
                )
            ],
        ]
    )
