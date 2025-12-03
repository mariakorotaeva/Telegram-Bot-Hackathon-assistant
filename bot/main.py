import asyncio
from aiogram import Bot, Dispatcher
from bot.config.config import config

async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())