import asyncio
import time
from collections import defaultdict

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

from bot.keyboards import main_menu, network_menu
from scanner.tester import test_hostname

router = Router()

# Simple per-user rate limit.
# Maximum 5 tests per user during a 60-second window.
RATE_LIMIT = 5
RATE_WINDOW = 60

user_tests = defaultdict(list)


def rate_limit_ok(user_id: int) -> bool:
    now = time.time()

    # Keep only timestamps from the current window.
    user_tests[user_id] = [
        timestamp
        for timestamp in user_tests[user_id]
        if now - timestamp < RATE_WINDOW
    ]

    if len(user_tests[user_id]) >= RATE_LIMIT:
        return False

    user_tests[user_id].append(now)
    return True


async def delete_later(message: Message, delay: int = 30):
    await asyncio.sleep(delay)

    try:
        await message.delete()
    except Exception:
        pass


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🇿🇲 <b>Zed SNI Scanner</b>\n\n"
        "Network connectivity diagnostics for authorized testing.\n\n"
        "Choose an option below:",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🧪 <b>Commands</b>\n\n"
        "/start - Open the scanner\n"
        "/test example.com - Test a hostname\n"
        "/help - Show this help\n\n"
        "Limit: 5 tests per user every 60 seconds.",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "network")
async def choose_network(callback: CallbackQuery):
    await callback.message.edit_text(
        "🇿🇲 <b>Select network</b>",
        reply_markup=network_menu(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("net:"))
async def network_selected(callback: CallbackQuery):
    network = callback.data.split(":", 1)[1]

    await callback.message.edit_text(
        f"📱 Selected: <b>{network}</b>\n\n"
        "Network-specific diagnostics will be available when "
        "an authorized test source is connected.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "test")
async def test_prompt(callback: CallbackQuery):
    await callback.message.answer(
        "🧪 Send a hostname to test:\n\n"
        "<code>/test example.com</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("test"))
async def test_command(message: Message):

    user_id = message.from_user.id

    # Rate limiting
    if not rate_limit_ok(user_id):
        warning = await message.answer(
            "⏳ <b>Slow down.</b>\n\n"
            "You've reached the limit of "
            "5 tests per minute.",
            parse_mode="HTML",
        )

        asyncio.create_task(delete_later(message, 10))
        asyncio.create_task(delete_later(warning, 10))
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        response = await message.answer(
            "Usage:\n<code>/test example.com</code>",
            parse_mode="HTML",
        )

        asyncio.create_task(delete_later(message, 15))
        asyncio.create_task(delete_later(response, 15))
        return

    hostname = parts[1].strip()

    # Send a compact testing message.
    status_message = await message.answer(
        f"🔎 Testing <code>{hostname}</code>...",
        parse_mode="HTML",
    )

    # Remove the user's command.
    asyncio.create_task(delete_later(message, 30))

    try:
        result = await test_hostname(hostname)

        status_icon = {
            "ACTIVE": "🟢",
            "UNSTABLE": "🟡",
            "DEAD": "🔴",
            "ERROR": "⚪",
        }.get(result["status"], "⚪")

        latency = result["latency_ms"]

        await status_message.edit_text(
            f"🧪 <code>{result['hostname']}</code>\n\n"
            f"{status_icon} <b>{result['status']}</b>"
            f" · {latency} ms\n\n"
            f"DNS {'✓' if result['dns'] else '✗'}  "
            f"TCP {'✓' if result['tcp'] else '✗'}  "
            f"TLS {'✓' if result['tls'] else '✗'}  "
            f"HTTPS {'✓' if result['https'] else '✗'}",
            parse_mode="HTML",
        )

    except Exception:
        await status_message.edit_text(
            "⚪ <b>Test failed</b>\n\n"
            "The hostname could not be tested.",
            parse_mode="HTML",
        )

    # Remove the result after 30 seconds.
    asyncio.create_task(delete_later(status_message, 30))


@router.callback_query(F.data == "status")
async def status(callback: CallbackQuery):
    await callback.message.edit_text(
        "📊 <b>Scanner Status</b>\n\n"
        "Core bot: 🟢 Online\n"
        "Hostname testing: 🟢 Available\n"
        "Rate limit: 5 tests / minute\n"
        "Network-specific agents: 🟡 Not connected",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )

    await callback.answer()
