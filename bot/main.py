import asyncio
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.handlers import router
from bot.monitor import monitor_hosts
from database.database import init_db


async def start_health_server() -> web.AppRunner:
    """Starts a lightweight HTTP health server so free cloud hosts (Render, Koyeb, etc.) keep the service healthy."""
    app = web.Application()

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    port = int(os.getenv("PORT", "8080"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Health check server listening on port {port}")
    return runner


async def main():
    load_dotenv()

    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "BOT_TOKEN is not configured."
        )

    # Initialize the database.
    init_db()

    # Start HTTP health endpoint for cloud platforms (Render, Koyeb, HF Spaces).
    health_runner = await start_health_server()

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
    monitor_task = asyncio.create_task(
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
        monitor_task.cancel()
        await bot.session.close()
        await health_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
