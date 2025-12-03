from aiogram import Router, types
from aiogram.filters import Command

# Создаем "роутер" для команд, связанных со стартом
router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Эта функция сработает, когда пользователь напишет /start
    welcome_text = (
        "👋 Привет! Я бот-помощник для хакатона.\n"
        "Я помогу тебе с расписанием, поиском команды и ответами на вопросы."
    )
    await message.answer(welcome_text)