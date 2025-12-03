import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логов
logging.basicConfig(level=logging.INFO)

async def main():
    # ==== ТОКЕН ====
    # Способ 1: Читаем из .env файла
    try:
        with open('.env', 'r') as f:
            token_line = f.read().strip()
            BOT_TOKEN = token_line.split('=', 1)[1]
    except:
        # Способ 2: Если .env нет, вставь токен прямо здесь
        BOT_TOKEN = "7123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"  # ← ЗАМЕНИ НА СВОЙ!
    
    print(f"🤖 Загружаю бота с токеном: {BOT_TOKEN[:15]}...")
    
    # Создаем бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # ===== ХЕНДЛЕРЫ =====
    # Самый простой хендлер на /start
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer("�� Бот запущен и работает!")
    
    # Хендлер на /help
    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        await message.answer("Доступные команды:\n/start - запуск\n/help - помощь")
    
    # Хендлер на любое сообщение
    @dp.message()
    async def echo(message: types.Message):
        await message.answer(f"Вы сказали: {message.text}")
    
    # ===== ЗАПУСК =====
    print("✅ Бот запускается... Пиши /start в Telegram!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
