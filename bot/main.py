from __future__ import annotations
import asyncio, signal
from aiogram import Bot, Dispatcher
from bot.config import settings
from bot.handlers.user import router
from db.database import init_db
from parser.lalafo import LalafoParser
from parser.scheduler import start_scheduler

parser = LalafoParser()

async def main() -> None:
    await init_db()
    bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    dp.include_router(router)
    start_scheduler(bot)
    print("✅ Бот запущен. Headless-браузер готов.")
    loop = asyncio.get_running_loop()
    async def shutdown() -> None:
        print("\n🛑 Завершаю работу...")
        await parser.close()
        await bot.session.close()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
