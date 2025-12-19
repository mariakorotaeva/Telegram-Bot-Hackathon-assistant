import asyncio
import logging
import sys
import os
import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Импорт роутеров
from bot.handlers import router  # ВСЕ роутеры уже здесь
from bot.handlers.notifications import schedule_reminder_checker
from bot.handlers.menu import temp_users_storage
# Импорт AI инициализации
from bot.handlers.ai_assistant import initialize_assistant

TOKEN = '8124039418:AAFiD-jK-NTtiJqYL868akQAg1u_zMwnpbQ'

# Создаем диспетчер
dp = Dispatcher()

# Включаем роутеры (ВСЕ в одном роутере)
dp.include_router(router)

async def on_startup():
    """Действия при запуске бота"""
    logging.info("🚀 Бот запускается...")
    
    # Инициализируем AI ассистента
    logging.info("🤖 Инициализация AI ассистента...")
    try:
        ai_ready = await initialize_assistant()
        if ai_ready:
            logging.info("✅ AI ассистент готов к работе!")
        else:
            logging.warning("⚠️ AI ассистент не инициализирован")
    except Exception as e:
        logging.error(f"❌ Ошибка инициализации AI ассистента: {e}")

async def on_shutdown():
    """Действия при остановке бота"""
    logging.info("🛑 Остановка бота...")

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
    
    # Создаем бота
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Запускаем проверку напоминаний
    asyncio.create_task(schedule_reminder_checker(bot, temp_users_storage))
    
    logger.info("✅ Бот запущен и готов к работе")
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