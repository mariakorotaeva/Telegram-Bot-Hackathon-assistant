"""
Telegram бот-ассистент для хакатонов
"""
import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode

# Импортируем из models
try:
    from models.ollama_handler import get_assistant
except ImportError:
    # Альтернативный импорт
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.ollama_handler import get_assistant

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env.example если .env нет
from dotenv import load_dotenv

# Пробуем загрузить .env, если нет - .env.example
env_file = '.env'
if not os.path.exists(env_file):
    env_file = '.env.example'
    logger.info(f"⚠️ Файл .env не найден, используем {env_file}")

load_dotenv(env_file)

# Конфигурация - используем разные возможные имена переменных
BOT_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.error(f"❌ BOT_TOKEN не найден в файле {env_file}!")
    logger.error("Добавьте BOT_TOKEN=ваш_токен в .env или .env.example файл")
    exit(1)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
assistant = get_assistant()

# Клавиатура
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Когда начало?")],
            [KeyboardButton(text="🎯 Темы хакатона")],
            [KeyboardButton(text="👥 Команды")],
            [KeyboardButton(text="🏆 Призы")],
            [KeyboardButton(text="❓ Задать вопрос")],
        ],
        resize_keyboard=True
    )

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = f"""
👋 Привет, {message.from_user.full_name}!

Я — бот-ассистент хакатона 🤖

Чем могу помочь:
• 📅 Расписание и даты
• 🎯 Темы и направления  
• 👥 Формирование команд
• 🏆 Призы и критерии
• 💡 Советы и помощь

Выбери вопрос или просто напиши его! ✨
"""
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

# Команда /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
📋 <b>Доступные команды:</b>

/start - Начать работу
/help - Помощь
/status - Проверить статус

📱 <b>Быстрые кнопки:</b>
• 📅 Когда начало?
• 🎯 Темы хакатона  
• 👥 Команды
• 🏆 Призы
• ❓ Задать вопрос

💬 <b>Просто напиши вопрос!</b>
Например:
"Какие технологии можно использовать?"
"Сколько человек в команде?"
"Где будет проходить?"
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# Команда /status
@dp.message(Command("status"))
async def cmd_status(message: Message):
    ollama_status = await assistant.test_connection()
    
    if ollama_status:
        model_info = assistant.get_model_info()
        status_text = f"""
✅ <b>Бот работает нормально!</b>

<b>Информация о модели:</b>
🤖 Модель: <code>{model_info['name']}</code>
🔗 Статус: <b>Подключено</b>

Готов отвечать на вопросы! 🚀
"""
    else:
        status_text = """
⚠️ <b>Ollama не доступен</b>

Проверьте что:
1. Ollama установлен
2. Сервер запущен: ollama serve
3. Модель загружена: ollama pull hackathon-assistant
"""
    
    await message.answer(status_text, parse_mode=ParseMode.HTML)

# Обработка быстрых кнопок
@dp.message(lambda message: message.text in [
    "📅 Когда начало?", "🎯 Темы хакатона", 
    "👥 Команды", "🏆 Призы", "❓ Задать вопрос"
])
async def handle_buttons(message: Message):
    question = message.text
    
    if question == "❓ Задать вопрос":
        await message.answer("💭 <b>Напишите ваш вопрос в чат!</b>", parse_mode=ParseMode.HTML)
        return
    
    # Показываем "печатает..."
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Преобразуем кнопку в вопрос
    questions_map = {
        "📅 Когда начало?": "Когда начало хакатона? Какое расписание?",
        "🎯 Темы хакатона": "Какие темы и направления хакатона?",
        "👥 Команды": "Как формируются команды? Сколько человек должно быть?",
        "🏆 Призы": "Какие призы и критерии оценки проектов?"
    }
    
    result = await assistant.ask(questions_map[question])
    
    if result['success']:
        response = f"""
<b>{question}</b>

{result['answer']}

<code>⏱️ {result['response_time']} | 🤖 {result['model']}</code>
"""
    else:
        response = f"""
⚠️ <b>Не удалось получить ответ</b>

{result['answer']}
"""
    
    await message.answer(response, parse_mode=ParseMode.HTML)

# Обработка всех сообщений
@dp.message()
async def handle_message(message: Message):
    user_question = message.text.strip()
    
    if len(user_question) < 3:
        await message.answer("📝 Напишите вопрос подробнее!")
        return
    
    logger.info(f"Вопрос от {message.from_user.id}: {user_question[:50]}...")
    
    # Показываем "печатает..."
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Временное сообщение
    temp_msg = await message.answer("🧠 <b>Думаю...</b>", parse_mode=ParseMode.HTML)
    
    # Получаем ответ
    result = await assistant.ask(user_question)
    
    # Удаляем временное сообщение
    try:
        await temp_msg.delete()
    except:
        pass
    
    if result['success']:
        response = f"""
<b>💬 Ваш вопрос:</b> <i>{user_question}</i>

<b>🤖 Ответ:</b>
{result['answer']}

<code>⏱️ {result['response_time']} | 🤖 {result['model']}</code>
"""
    else:
        response = f"""
⚠️ <b>Ошибка</b>

{result['answer']}

Попробуйте переформулировать вопрос.
"""
    
    await message.answer(response, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())

# Главная функция
async def main():
    logger.info("🚀 Запуск бота хакатон-ассистента...")
    
    # Проверяем подключение
    logger.info("🔗 Проверка подключения к Ollama...")
    if await assistant.test_connection():
        logger.info("✅ Ollama доступен!")
    else:
        logger.warning("⚠️ Ollama не доступен!")
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен")
