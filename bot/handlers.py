import asyncio
import time
import re
from collections import defaultdict

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

from bot.keyboards import main_menu, network_selection_keyboard
from scanner.tester import test_hostname
from database.database import (
    save_result,
    get_hostname_stats,
    get_top_hostnames,
    add_monitored_host,
    remove_monitored_host,
    get_monitored_hosts,
    share_community_host,      # NEW: For community sharing
    get_top_community_hosts,   # NEW: For top community hosts
)

router = Router()

# Rate limiting configuration
RATE_LIMIT = 5
RATE_WINDOW = 60
user_tests = defaultdict(list)

# Custom scan state tracking
user_custom_scan = {}

# Real Zambian network hostnames
NETWORK_HOSTNAMES = {
    "mtn": [
        "mtnid.mtn.zm", 
        "imbankgroup.com", 
        "m.drct.me"
    ],
    "airtel": [
        "google.com", "airtel.co.zm"
    ],
    "zamtel": [
        "apps.zamtel.co.zm", 
        "prod.zamtelkwacha.co.zm", 
        "pprod.zamtelkwacha.co.zm"
    ],
}

def rate_limit_ok(user_id: int) -> bool:
    now = time.time()
    user_tests[user_id] = [
        timestamp
        for timestamp in user_tests[user_id]
        if now - timestamp < RATE_WINDOW
    ]
    if len(user_tests[user_id]) >= RATE_LIMIT:
        return False
    user_tests[user_id].append(now)
    return True

async def delete_later(message: Message, delay: int = 20):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🇿🇲 <b>Zed SNI Scanner</b>\n\n"
        "Real hostname connectivity diagnostics.\n\n"
        "🧪 <b>Commands:</b>\n"
        "/test google.com\n"
        "/monitor google.com\n"
        "/monitored\n"
        "/unmonitor google.com\n"
        "/scan\n"
        "/stats google.com\n"
        "/share zamtel apps.zamtel.co.zm\n"
        "/top_zm\n\n"
        "Choose an option below:",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )

@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🧪 <b>How to use Zed SNI Scanner</b>\n\n"
        "<b>Test:</b>\n"
        "<code>/test google.com</code>\n\n"
        "<b>Monitor:</b>\n"
        "<code>/monitor google.com</code>\n\n"
        "<b>View monitoring:</b>\n"
        "<code>/monitored</code>\n\n"
        "<b>Stop monitoring:</b>\n"
        "<code>/unmonitor google.com</code>\n\n"
        "<b>Scan network:</b>\n"
        "<code>/scan</code>\n\n"
        "<b>View stats:</b>\n"
        "<code>/stats google.com</code>\n\n"
        "<b>Share a working host:</b>\n"
        "<code>/share mtn mtnid.mtn.zm</code>\n\n"
        "<b>Top community hosts:</b>\n"
        "<code>/top_zm</code>\n\n"
        "🟢 ACTIVE = Connection successful\n"
        "🟡 UNSTABLE = Partial connection\n"
        "🔴 DEAD = Connection failed\n\n"
        "⏱️ Manual test limit: 5 tests per user every 60 seconds.",
        parse_mode="HTML",
    )

# --- NEW: SHARE COMMAND ---
@router.message(Command("share"))
async def share_command(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        response = await message.answer(
            "❌ <b>Usage error.</b>\n\n"
            "Use format:\n"
            "<code>/share [network] [hostname]</code>\n\n"
            "Example:\n"
            "<code>/share mtn mtnid.mtn.zm</code>",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(response, 20))
        return

    network = parts[1].strip().lower()
    hostname = parts[2].strip()

    allowed_networks = ["mtn", "airtel", "zamtel", "global"]
    if network not in allowed_networks:
        response = await message.answer(
            f"❌ <b>Invalid network.</b>\n\n"
            f"Allowed networks: mtn, airtel, zamtel, global",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(response, 20))
        return

    user_id = message.from_user.id
    success = share_community_host(hostname, network, user_id)

    if success:
        response = await message.answer(
            f"✅ <b>Host shared successfully!</b>\n\n"
            f"Network: <b>{network.capitalize()}</b>\n"
            f"Host: <code>{hostname}</code>\n\n"
            f"Use <code>/top_zm</code> to see all community-hosted SNI hosts.",
            parse_mode="HTML",
        )
    else:
        response = await message.answer(
            f"⚠️ <b>Already shared.</b>\n\n"
            f"<code>{hostname}</code> has already been shared for {network.capitalize()} by the community.",
            parse_mode="HTML",
        )
    
    asyncio.create_task(delete_later(response, 20))

# --- NEW: TOP_ZM COMMAND ---
@router.message(Command("top_zm"))
async def top_zm_command(message: Message):
    top_hosts = get_top_community_hosts(5)

    if not top_hosts:
        response = await message.answer(
            "📭 <b>No community hosts yet.</b>\n\n"
            "Be the first to share a working SNI host!\n"
            "Use: <code>/share mtn mtnid.mtn.zm</code>",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(response, 20))
        return

    text = "🏆 <b>TOP COMMUNITY VERIFIED HOSTS</b>\n\n"
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for index, item in enumerate(top_hosts):
        medal = medals[index] if index < 5 else f"{index+1}."
        text += (
            f"{medal} <code>{item['hostname']}</code>\n"
            f"   📱 Network: <b>{item['network'].capitalize()}</b>\n"
            f"   👥 Shares: {item['share_count']}\n"
            f"   🕒 Last shared: {item['last_shared_at']}\n\n"
        )

    response = await message.answer(text, parse_mode="HTML")
    asyncio.create_task(delete_later(response, 30))

@router.message(Command("stats"))
async def stats_command(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        response = await message.answer(
            "❌ <b>Missing hostname.</b>\n\n"
            "Use:\n"
            "<code>/stats google.com</code>",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(response, 20))
        return

    hostname = parts[1].strip()
    stats = get_hostname_stats(hostname)

    if stats is None:
        response = await message.answer(
            f"📊 <b>No data for {hostname}</b>\n\n"
            "This hostname has never been tested by the bot.\n"
            "Use <code>/test {hostname}</code> to start collecting data.",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(response, 20))
        return

    avg_lat = f"{stats['avg_latency']} ms" if stats['avg_latency'] else "N/A"
    best_lat = f"{stats['best_latency']} ms" if stats['best_latency'] else "N/A"
    worst_lat = f"{stats['worst_latency']} ms" if stats['worst_latency'] else "N/A"

    uptime_emoji = "🟢" if stats['uptime_percent'] >= 95 else "🟡" if stats['uptime_percent'] >= 70 else "🔴"

    text = (
        f"📊 <b>Stats for {hostname}</b>\n\n"
        f"{uptime_emoji} Uptime: <b>{stats['uptime_percent']}%</b>\n"
        f"🧪 Total tests: {stats['total_tests']}\n"
        f"✅ Active tests: {stats['active_tests']}\n\n"
        f"⚡ Average latency: <b>{avg_lat}</b>\n"
        f"🚀 Best latency: {best_lat}\n"
        f"🐌 Worst latency: {worst_lat}\n\n"
        f"🕒 Last checked: {stats['last_check']}"
    )

    response = await message.answer(text, parse_mode="HTML")
    asyncio.create_task(delete_later(response, 30))

@router.message(Command("monitor"))
async def monitor_command(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        response = await message.answer(
            "❌ <b>Missing hostname.</b>\n\n"
            "Use:\n"
            "<code>/monitor google.com</code>",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(response, 20))
        return

    hostname = parts[1].strip()
    if "://" in hostname or "/" in hostname:
        response = await message.answer(
            "❌ Please enter a hostname only.\n\n"
            "Example:\n"
            "<code>/monitor google.com</code>",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(response, 20))
        return

    status_message = await message.answer(
        f"🔎 Checking <code>{hostname}</code> before monitoring...",
        parse_mode="HTML",
    )

    try:
        result = await test_hostname(hostname)
        save_result(
            hostname=result["hostname"],
            status=result["status"],
            dns=result["dns"],
            tcp=result["tcp"],
            tls=result["tls"],
            https=result["https"],
            latency_ms=result["latency_ms"] if isinstance(result["latency_ms"], int) else None,
        )
        add_monitored_host(hostname)

        icon = {
            "ACTIVE": "🟢",
            "UNSTABLE": "🟡",
            "DEAD": "🔴",
            "ERROR": "⚪",
        }.get(result["status"], "⚪")

        await status_message.edit_text(
            f"🔄 <b>Monitoring enabled</b>\n\n"
            f"🌐 <code>{hostname}</code>\n"
            f"{icon} Current status: <b>{result['status']}</b>\n"
            f"⚡ Latency: {result['latency_ms']} ms\n\n"
            "The bot will automatically check this hostname "
            "every 5 minutes.",
            parse_mode="HTML",
        )
    except Exception as error:
        print(f"Monitor setup error for {hostname}: {error}")
        await status_message.edit_text(
            "❌ <b>Could not start monitoring.</b>\n\n"
            "The hostname could not be tested.",
            parse_mode="HTML",
        )

    asyncio.create_task(delete_later(status_message, 20))

@router.message(Command("unmonitor"))
async def unmonitor_command(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        response = await message.answer(
            "❌ <b>Missing hostname.</b>\n\n"
            "Use:\n"
            "<code>/unmonitor google.com</code>",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(response, 20))
        return

    hostname = parts[1].strip()
    remove_monitored_host(hostname)

    response = await message.answer(
        f"🛑 Monitoring stopped for:\n"
        f"<code>{hostname}</code>",
        parse_mode="HTML",
    )
    asyncio.create_task(delete_later(response, 20))

@router.message(Command("monitored"))
async def monitored_command(message: Message):
    hosts = get_monitored_hosts()
    if not hosts:
        response = await message.answer(
            "📋 <b>Monitored Hosts</b>\n\n"
            "No hostnames are currently being monitored.",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(response, 20))
        return

    text = "📋 <b>MONITORED HOSTS</b>\n\n"
    for row in hosts:
        (host_id, hostname, network, enabled, last_status, last_latency, last_checked) = row
        icon = {
            "ACTIVE": "🟢",
            "UNSTABLE": "🟡",
            "DEAD": "🔴",
            None: "⚪",
        }.get(last_status, "⚪")
        latency = f"{last_latency}ms" if last_latency is not None else "N/A"
        text += (
            f"{icon} <code>{hostname}</code>\n"
            f"   ⚡ {latency}\n"
            f"   Last check: {last_checked or 'Pending'}\n\n"
        )

    response = await message.answer(text, parse_mode="HTML")
    asyncio.create_task(delete_later(response, 20))

@router.callback_query(F.data == "network")
async def choose_network(callback: CallbackQuery):
    await callback.message.edit_text(
        "🇿🇲 <b>Select a Zambian network</b>",
        reply_markup=network_selection_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()

@router.callback_query(F.data.startswith("net:"))
async def network_selected(callback: CallbackQuery):
    network = callback.data.split(":", 1)[1]
    await callback.message.edit_text(
        f"📱 Selected network: <b>{network}</b>\n\n"
        "Network selection is ready for diagnostics.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )
    await callback.answer()

@router.callback_query(F.data == "test")
async def test_prompt(callback: CallbackQuery):
    await callback.message.answer(
        "🧪 Send the hostname you want to test.\n\n"
        "Example:\n"
        "<code>/test google.com</code>",
        parse_mode="HTML",
    )
    await callback.answer()

@router.message(Command("test"))
async def test_command(message: Message):
    user_id = message.from_user.id
    if not rate_limit_ok(user_id):
        warning = await message.answer(
            "⏳ <b>Slow down.</b>\n\n"
            "You've reached the limit of "
            "5 tests per minute.",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(message, 20))
        asyncio.create_task(delete_later(warning, 20))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        response = await message.answer(
            "❌ <b>Missing hostname.</b>\n\n"
            "Use:\n"
            "<code>/test google.com</code>",
            parse_mode="HTML",
        )
        asyncio.create_task(delete_later(message, 20))
        asyncio.create_task(delete_later(response, 20))
        return

    hostname = parts[1].strip()
    status_message = await message.answer(
        f"🔎 Testing <code>{hostname}</code>...",
        parse_mode="HTML",
    )
    asyncio.create_task(delete_later(message, 20))

    try:
        result = await test_hostname(hostname)
        save_result(
            hostname=result["hostname"],
            status=result["status"],
            dns=result["dns"],
            tcp=result["tcp"],
            tls=result["tls"],
            https=result["https"],
            latency_ms=result["latency_ms"] if isinstance(result["latency_ms"], int) else None,
        )
        status_icon = {
            "ACTIVE": "🟢",
            "UNSTABLE": "🟡",
            "DEAD": "🔴",
            "ERROR": "⚪",
        }.get(result["status"], "⚪")

        await status_message.edit_text(
            f"🧪 <code>{result['hostname']}</code>\n\n"
            f"{status_icon} <b>{result['status']}</b>"
            f" · {result['latency_ms']} ms\n\n"
            f"DNS {'✓' if result['dns'] else '✗'}  "
            f"TCP {'✓' if result['tcp'] else '✗'}  "
            f"TLS {'✓' if result['tls'] else '✗'}  "
            f"HTTPS {'✓' if result['https'] else '✗'}",
            parse_mode="HTML",
        )
    except Exception as error:
        print(f"Test error for {hostname}: {error}")
        await status_message.edit_text(
            "⚪ <b>Test failed</b>\n\n"
            "The hostname could not be tested.",
            parse_mode="HTML",
        )

    asyncio.create_task(delete_later(status_message, 20))

@router.callback_query(F.data == "status")
async def status(callback: CallbackQuery):
    rankings = get_top_hostnames(5)
    text = (
        "📊 <b>ZED SNI SCANNER</b>\n\n"
        "🟢 Core bot: Online\n"
        "🟢 Hostname testing: Available\n"
        "🟢 Database: Recording results\n\n"
        "🏆 <b>TOP HOSTNAMES</b>\n\n"
    )

    if not rankings:
        text += "No test results available yet."
    else:
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for index, item in enumerate(rankings):
            medal = medals[index]
            latency = f"{item['average_latency']}ms" if item["average_latency"] is not None else "N/A"
            text += (
                f"{medal} <code>{item['hostname']}</code>\n"
                f"   🟢 Success: {item['success_rate']}%\n"
                f"   ⚡ Avg latency: {latency}\n"
                f"   🧪 Tests: {item['total_tests']}\n\n"
            )

    await callback.message.edit_text(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML",
    )
    await callback.answer()

# --- NETWORK SCANNING LOGIC ---

@router.message(Command("scan"))
async def scan_command(message: Message):
    await message.answer(
        "🇿🇲 <b>Select a Zambian network to scan for active SNI hosts:</b>",
        reply_markup=network_selection_keyboard(),
        parse_mode="HTML",
    )

async def run_network_scan(message: Message, network_label: str, hostnames: list):
    status_msg = await message.answer(
        f"🔎 Scanning <b>{network_label}</b> network for active SNI hosts...\n\n"
        f"Testing {len(hostnames)} hostnames. Please wait...",
        parse_mode="HTML",
    )

    results = []
    for i, host in enumerate(hostnames):
        try:
            result = await test_hostname(host)
            save_result(
                hostname=result["hostname"],
                status=result["status"],
                dns=result["dns"],
                tcp=result["tcp"],
                tls=result["tls"],
                https=result["https"],
                latency_ms=result["latency_ms"] if isinstance(result["latency_ms"], int) else None,
            )
            if result["status"] == "ACTIVE":
                results.append(f"✅ {result['hostname']} ({result['latency_ms']} ms)")
            elif result["status"] == "UNSTABLE":
                results.append(f"🟡 {result['hostname']} ({result['latency_ms']} ms)")
            else:
                results.append(f"❌ {result['hostname']}")

            if (i + 1) % 3 == 0 or (i + 1) == len(hostnames):
                active_count = sum(1 for r in results if "✅" in r)
                await status_msg.edit_text(
                    f"🔎 Scanning <b>{network_label}</b>...\n\n"
                    f"Tested {i + 1}/{len(hostnames)}\n\n"
                    f"✅ Working: {active_count}",
                    parse_mode="HTML",
                )
            await asyncio.sleep(0.5)
        except Exception as e:
            results.append(f"❌ {host} (Error)")
            print(f"Scan error for {host}: {e}")

    working_hosts = [r for r in results if "✅" in r]
    text = f"📊 <b>Scan complete for {network_label}</b>\n\n"
    if working_hosts:
        text += f"✅ <b>Working SNI hosts ({len(working_hosts)}):</b>\n"
        for w in working_hosts:
            clean_w = w.replace("✅ ", "").replace("🟡 ", "").replace("❌ ", "")
            text += f"<code>{clean_w}</code>\n"
        text += "\n"
    else:
        text += "❌ No active SNI hosts found for this network.\n\n"

    text += f"📝 Total tested: {len(results)}\n"
    text += f"🟢 Active: {len(working_hosts)}"

    await status_msg.edit_text(text, parse_mode="HTML")
    asyncio.create_task(delete_later(status_msg, 20))

@router.callback_query(F.data == "scan_mtn")
async def scan_mtn(callback: CallbackQuery):
    await callback.answer()
    hostnames = NETWORK_HOSTNAMES.get("mtn", [])
    asyncio.create_task(run_network_scan(callback.message, "MTN Zambia", hostnames))

@router.callback_query(F.data == "scan_airtel")
async def scan_airtel(callback: CallbackQuery):
    await callback.answer()
    hostnames = NETWORK_HOSTNAMES.get("airtel", [])
    asyncio.create_task(run_network_scan(callback.message, "Airtel Zambia", hostnames))

@router.callback_query(F.data == "scan_zamtel")
async def scan_zamtel(callback: CallbackQuery):
    await callback.answer()
    hostnames = NETWORK_HOSTNAMES.get("zamtel", [])
    asyncio.create_task(run_network_scan(callback.message, "Zamtel Zambia", hostnames))

@router.callback_query(F.data == "scan_custom")
async def scan_custom_prompt(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "📝 <b>Custom Network Scan</b>\n\n"
        "Please type the hostnames you want to test (one per line, or separated by spaces/commas).\n\n"
        "Example:\n"
        "<code>myvpn.com api.mysite.com</code>\n\n"
        "Se
