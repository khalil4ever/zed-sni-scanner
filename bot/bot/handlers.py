from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

from bot.keyboards import main_menu, network_menu
from scanner.tester import test_hostname

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🇿🇲 <b>Zed SNI Scanner</b>\n\n"
        "Connectivity diagnostics for authorized testing.\n\n"
        "Choose an option below:",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🧪 <b>Commands</b>\n\n"
        "/start - Open the main menu\n"
        "/test example.com - Test a hostname\n"
        "/help - Show this help\n\n"
        "Network-specific verification will require authorized "
        "test agents connected to the relevant networks.",
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
        "Network-specific testing will become available when an "
        "authorized tester for this network is connected.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "test")
async def test_prompt(callback: CallbackQuery):
    await callback.message.answer(
        "🧪 Send a hostname to test, for example:\n\n"
        "<code>/test example.com</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("test"))
async def test_command(message: Message):
    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        await message.answer(
            "Usage:\n<code>/test example.com</code>",
            parse_mode="HTML",
        )
        return

    hostname = parts[1].strip()

    result = await test_hostname(hostname)

    status_icon = {
        "ACTIVE": "🟢",
        "UNSTABLE": "🟡",
        "DEAD": "🔴",
        "ERROR": "⚪",
    }.get(result["status"], "⚪")

    await message.answer(
        f"🧪 <b>Hostname Test</b>\n\n"
        f"Hostname: <code>{result['hostname']}</code>\n\n"
        f"DNS: {'✓' if result['dns'] else '✗'}\n"
        f"TCP: {'✓' if result['tcp'] else '✗'}\n"
        f"TLS/SNI: {'✓' if result['tls'] else '✗'}\n"
        f"HTTPS: {'✓' if result['https'] else '✗'}\n"
        f"Latency: {result['latency_ms']} ms\n\n"
        f"{status_icon} <b>{result['status']}</b>\n"
        f"{result['detail']}",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "status")
async def status(callback: CallbackQuery):
    await callback.message.edit_text(
        "📊 <b>Scanner Status</b>\n\n"
        "Core bot: 🟢 Online\n"
        "Public hostname testing: 🟢 Available\n"
        "Network-specific agents: 🟡 Not connected\n"
        "Database: 🟢 Local SQLite\n\n"
        "No carrier-specific result is reported until an "
        "authorized network tester verifies it.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )

    await callback.answer()
