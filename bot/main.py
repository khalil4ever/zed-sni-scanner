import asyncio
import os

from aiogram import Bot, Dispatcher

from bot.handlers import router
from bot.monitor import monitor_hosts
from database.database import init_db


async def main():
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "BOT_TOKEN is not configured."
        )

    # Initialize the database.
    init_db()

    bot = Bot(token=token)

    dp = Dispatcher()

    dp.include_router(router)

    # Optional channel for monitoring alerts.
    channel_id = os.getenv("MONITOR_CHANNEL_ID")

    if channel_id:
        try:
            channel_id = int(channel_id)
        except ValueError:
            print(
                "MONITOR_CHANNEL_ID is not a valid number."
            )
            channel_id = None

    # Start the monitoring worker.
    asyncio.create_task(
        monitor_hosts(
            bot=bot,
            channel_id=channel_id,
        )
    )

    print("🇿🇲 Zed SNI Scanner is starting...")
    print("🔄 Monitoring worker started.")

    try:
        await dp.start_polling(bot)

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
