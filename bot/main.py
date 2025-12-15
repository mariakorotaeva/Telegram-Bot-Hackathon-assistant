import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.handlers import router
from bot.handlers.notifications import schedule_reminder_checker
from bot.handlers.menu import temp_users_storage
from bot.models.ollama_handler import get_assistant, OllamaHandler

TOKEN = '8124039418:AAFiD-jK-NTtiJqYL868akQAg1u_zMwnpbQ'

dp = Dispatcher()
dp.include_router(router)

ollama_assistant: OllamaHandler = None

async def initialize_assistant():
    """Инициализация Ollama ассистента"""
    global ollama_assistant
    
    try:
        ollama_assistant = get_assistant()
        await ollama_assistant.initialize()
        
        # Проверяем подключение к Ollama
        if await ollama_assistant.test_connection():
            logging.info("✅ Ollama подключен и готов к работе")
        else:
            logging.warning("⚠️ Ollama не доступен. Ассистент будет работать в ограниченном режиме")
    
    except Exception as e:
        logging.error(f"❌ Ошибка инициализации Ollama: {e}")
        ollama_assistant = None

async def on_startup():
    """Действия при запуске бота"""
    logging.info("🚀 Бот запускается...")
    
    # Инициализируем Ollama ассистента
    await initialize_assistant()
    
    # Проверяем наличие Ollama и выводим статус
    if ollama_assistant and ollama_assistant._model_loaded:
        logging.info(f"Модель {ollama_assistant.model_name} загружена и готова")
    else:
        logging.warning("Ollama не доступен, AI-функциональность будет ограничена")

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    asyncio.create_task(schedule_reminder_checker(bot, temp_users_storage))
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())