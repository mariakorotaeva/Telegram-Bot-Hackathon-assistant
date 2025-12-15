import asyncio
import logging
import sys
import signal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Импорт роутеров
from bot.handlers import router
from bot.handlers.notifications import schedule_reminder_checker
from bot.handlers.menu import temp_users_storage
# Импорт AI роутера
from bot.handlers.ai_assistent import router as ai_router

# Импорт Ollama
from models.ollama_handler import get_assistant, OllamaHandler

TOKEN = '8124039418:AAFiD-jK-NTtiJqYL868akQAg1u_zMwnpbQ'

# Создаем диспетчер
dp = Dispatcher()

# Включаем роутеры
dp.include_router(router)
dp.include_router(ai_router)  # Добавляем AI роутер!

# Глобальный экземпляр обработчика Ollama
ollama_assistant: OllamaHandler = None

async def initialize_assistant():
    """Инициализация Ollama ассистента с прогревом на 5 токенов"""
    global ollama_assistant
    
    try:
        logging.info("🚀 Инициализация AI ассистента...")
        ollama_assistant = get_assistant()
        
        # Проверяем подключение к Ollama
        logging.info("🔄 Проверка подключения к Ollama...")
        is_connected = await ollama_assistant.test_connection()
        
        if not is_connected:
            logging.error("❌ Ollama недоступен! Запустите: ollama serve")
            logging.warning("🤖 AI-функциональность будет отключена")
            return False
        
        logging.info("✅ Ollama подключен")
        
        # Прогреваем модель на 5 токенов
        logging.info(f"🔥 Прогрев модели {ollama_assistant.model_name} на 5 токенов...")
        warmup_success = await ollama_assistant.initialize()
        
        if warmup_success:
            logging.info(f"✅ Модель {ollama_assistant.model_name} прогрета и готова к работе")
            return True
        else:
            logging.warning("⚠️ Модель не прогрета, первый запрос будет медленным")
            # Но все равно отмечаем, что модель доступна
            ollama_assistant._model_loaded = True
            return True
            
    except Exception as e:
        logging.error(f"❌ Ошибка инициализации Ollama: {e}")
        ollama_assistant = None
        return False

async def on_startup():
    """Действия при запуске бота"""
    logging.info("🚀 Бот запускается...")
    
    # Инициализируем Ollama ассистента
    ai_ready = await initialize_assistant()
    
    if ai_ready and ollama_assistant:
        # Получаем информацию о модели
        info = ollama_assistant.get_model_info()
        logging.info(f"🤖 AI-ассистент готов!")
        logging.info(f"   Модель: {info['name']}")
        logging.info(f"   Статус: {'🟢 Загружена' if info['loaded'] else '🟡 Загрузка'}")
        logging.info(f"   Кэш: {info['cache_size']} вопросов")
        logging.info(f"   Токены прогрева: {info['warmup_tokens']}")
    else:
        logging.warning("⚠️ AI-ассистент недоступен")
        logging.warning("   Функция 'Задать вопрос AI' будет отключена")

async def on_shutdown():
    """Действия при остановке бота"""
    logging.info("🛑 Остановка бота...")
    
    if ollama_assistant:
        # Можно сохранить кэш или выполнить другие действия
        cache_size = len(ollama_assistant._response_cache)
        logging.info(f"💾 Сохранено {cache_size} вопросов в кэше")

async def main() -> None:
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    logger = logging.getLogger(__name__)
    
    # Регистрируем обработчики событий
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запускаем инициализацию
    await on_startup()
    
    # Создаем бота
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Запускаем проверку напоминаний
    asyncio.create_task(schedule_reminder_checker(bot, temp_users_storage))
    
    logger.info("✅ Бот запущен и готов к работе")
    logger.info("🤖 Для проверки AI используйте /ai_status")
    logger.info("📋 Для меню используйте /menu")
    
    # Запускаем polling
    await dp.start_polling(bot)

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logging.info(f"📶 Получен сигнал {signum}, завершаем работу...")
    sys.exit(0)

if __name__ == "__main__":
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("⏹️ Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logging.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)