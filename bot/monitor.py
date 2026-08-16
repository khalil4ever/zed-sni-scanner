import asyncio
import os
from aiogram import Bot
from database.database import (
    get_monitored_hosts,
    update_monitored_host,
)
from scanner.tester import test_hostname

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONITOR_CHANNEL_ID = os.getenv("MONITOR_CHANNEL_ID")
CHECK_INTERVAL = 300  # 5 minutes

async def monitor_hosts(bot=None, channel_id=None):
    """
    Background worker that runs every 5 minutes.
    Accepts a bot and channel_id (or uses environment variables).
    Tests monitored hosts and sends alerts if status changes.
    """
    # Use passed bot, or create a new one if none was passed
    if bot is None:
        bot = Bot(token=BOT_TOKEN)
    
    # Use passed channel_id, or fallback to env variable
    if channel_id is None:
        channel_id = MONITOR_CHANNEL_ID

    while True:
        try:
            hosts = get_monitored_hosts()
            
            for host_row in hosts:
                # Unpack the row: (id, hostname, network, enabled, last_status, last_latency, last_checked)
                host_id, hostname, network, enabled, last_status, last_latency_ms, last_checked_at = host_row

                if not enabled:
                    continue

                try:
                    # Test the hostname live
                    result = await test_hostname(hostname)
                    new_status = result["status"]
                    new_latency = result["latency_ms"]
                    
                    # Always update the database with the latest result
                    update_monitored_host(hostname, new_status, new_latency)

                    # --- ALERT LOGIC ---
                    # Only trigger alerts if a channel ID exists and the status actually changed
                    if channel_id and last_status != new_status:
                        message = None
                        
                        if new_status in ["DEAD", "ERROR"] and last_status not in ["DEAD", "ERROR"]:
                            # Host just went DOWN
                            message = (
                                f"🔴 <b>HOSTNAME DOWN</b>\n\n"
                                f"🌐 {hostname}\n"
                                f"❌ Status: {new_status}\n"
                                f"⚡ Previous: {last_status or 'Unknown'}"
                            )
                        elif new_status == "ACTIVE" and last_status not in ["ACTIVE", None]:
                            # Host just came BACK UP
                            message = (
                                f"🟢 <b>HOSTNAME RESTORED</b>\n\n"
                                f"🌐 {hostname}\n"
                                f"✅ Status: {new_status}\n"
                                f"⚡ Latency: {new_latency} ms"
                            )

                        if message:
                            try:
                                await bot.send_message(chat_id=channel_id, text=message, parse_mode="HTML")
                            except Exception as e:
                                print(f"Failed to send alert for {hostname}: {e}")

                except Exception as e:
                    print(f"Monitoring error for {hostname}: {e}")

                # Small delay between checking hosts to prevent rate limits
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Monitor loop error: {e}")

        # Wait 5 minutes before the next full scan
        await asyncio.sleep(CHECK_INTERVAL)
