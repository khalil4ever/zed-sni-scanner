import asyncio
import os

from aiogram import Bot, Dispatcher

from bot.handlers import router
from database.database import init_db


async def main():
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "BOT_TOKEN is not configured."
        )

    # Initialize the database before the bot starts.
    init_db()

    bot = Bot(token=token)

    dp = Dispatcher()

    dp.include_router(router)

    print("🇿🇲 Zed SNI Scanner is starting...")

    try:
        await dp.start_polling(bot)

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
