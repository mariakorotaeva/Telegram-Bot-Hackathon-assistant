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
    """Инициализация Ollama ассистента с вашими оптимизациями"""
    global ollama_assistant
    
    try:
        ollama_assistant = get_assistant()
        
        # ВАШ КОД: Инициализация с прогреванием модели
        if hasattr(ollama_assistant, 'initialize'):
            await ollama_assistant.initialize()
        else:
            # Альтернативная инициализация для старой версии
            await ollama_assistant._warmup_model()
        
        # Проверяем подключение к Ollama
        if await ollama_assistant.test_connection():
            logging.info("✅ Ollama подключен и готов к работе")
            
            # ВАШ КОД: Предопределенные ответы для быстрого доступа
            if hasattr(ollama_assistant, '_predefined_responses'):
                logging.info(f"⚡ Загружено {len(ollama_assistant._predefined_responses)} предопределенных ответов")
            
            # ВАШ КОД: Проверка кэша
            if hasattr(ollama_assistant, '_response_cache'):
                logging.info(f"💾 Кэш инициализирован")
                
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
    if ollama_assistant:
        model_status = "не загружена"
        if hasattr(ollama_assistant, '_model_loaded') and ollama_assistant._model_loaded:
            model_status = "загружена"
        
        # ВАШ КОД: Информация о модели с вашими оптимизациями
        model_info = ollama_assistant.get_model_info()
        logging.info(f"🤖 Модель: {model_info.get('name', 'N/A')} ({model_status})")
        
        if hasattr(ollama_assistant, '_model_loaded'):
            if ollama_assistant._model_loaded:
                logging.info("🔥 Модель прогрета и готова к работе")
            else:
                logging.warning("⚠️ Модель не прогрета, первый запрос будет медленным")
    else:
        logging.warning("Ollama не доступен, AI-функциональность будет ограничена")

async def main() -> None:
    # Выполняем действия при запуске
    await on_startup()
    
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    asyncio.create_task(schedule_reminder_checker(bot, temp_users_storage))
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # ВАШ КОД: Обработка KeyboardInterrupt
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("⏹️ Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"❌ Критическая ошибка: {e}")