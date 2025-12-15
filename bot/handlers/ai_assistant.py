import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sys
import os

# Добавляем путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Импортируем настоящий AI
try:
    from models.ollama_handler import get_assistant
    assistant = get_assistant()
    AI_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ AI Assistant загружен")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки AI: {e}")
    assistant = None
    AI_AVAILABLE = False

router = Router()

# Клавиатура для выхода - всегда видна!
def get_ai_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚪 Выйти из AI")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False  # Важно! Клавиатура не скрывается
    )


class AIState(StatesGroup):
    active = State()  # Пользователь в режиме AI


@router.callback_query(F.data == "ask_ai_question")
async def start_ai_callback(callback: CallbackQuery, state: FSMContext):
    """Начало по кнопке из меню"""
    if not AI_AVAILABLE:
        await callback.answer("⚠️ AI недоступен", show_alert=True)
        return
    
    await callback.message.answer(
        "🤖 <b>AI-ассистент активирован!</b>\n\n"
        "Задавайте вопросы о хакатоне в этот чат!\n\n"
        "<i>Кнопка выхода всегда внизу👇</i>",
        parse_mode="HTML",
        reply_markup=get_ai_keyboard()  # Показываем клавиатуру сразу!
    )
    
    await state.set_state(AIState.active)
    await callback.answer()


@router.message(Command("ai"))
async def start_ai_command(message: Message, state: FSMContext):
    """Начало по команде /ai"""
    if not AI_AVAILABLE:
        await message.answer("⚠️ AI ассистент недоступен")
        return
    
    await message.answer(
        "🤖 <b>Режим AI-ассистента включен</b>\n\n"
        "Спрашивайте что угодно о хакатоне!\n\n"
        "<i>Чтобы выйти - жмите кнопку внизу</i>",
        parse_mode="HTML",
        reply_markup=get_ai_keyboard()  # Клавиатура здесь!
    )
    
    await state.set_state(AIState.active)


@router.message(F.text == "🚪 Выйти из AI")
async def exit_ai(message: Message, state: FSMContext):
    """Выход по кнопке - работает всегда!"""
    await state.clear()
    await message.answer(
        "✅ <b>Вы вышли из режима AI</b>\n\n"
        "Используйте /menu для возврата в меню",
        parse_mode="HTML",
        reply_markup=None  # Убираем клавиатуру
    )


@router.message(AIState.active)
async def handle_real_ai_question(message: Message):
    """Обработка вопросов с настоящим AI"""
    # Пропускаем кнопку выхода (уже обработано выше)
    if message.text == "🚪 Выйти из AI":
        return
    
    question = message.text.strip()
    
    if len(question) < 3:
        await message.answer(
            "❓ Вопрос слишком короткий\nПопробуйте подробнее:",
            reply_markup=get_ai_keyboard()  # Кнопка остается!
        )
        return
    
    if not AI_AVAILABLE or not assistant:
        await message.answer(
            "⚠️ AI временно недоступен\nПопробуйте позже",
            reply_markup=get_ai_keyboard()
        )
        return
    
    # Показываем "печатает..."
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # НАСТОЯЩИЙ вызов AI!
        result = await assistant.ask(question)
        
        if result.get('success'):
            response = f"""
💬 <b>Ваш вопрос:</b>
<i>{question}</i>

🤖 <b>Ответ:</b>
{result['answer']}
"""
        else:
            response = f"⚠️ Ошибка: {result.get('answer', 'Попробуйте снова')}"
        
        # Отправляем ответ с клавиатурой (кнопка выхода остается!)
        await message.answer(
            response,
            parse_mode="HTML",
            reply_markup=get_ai_keyboard()  # Важно! Клавиатура прикрепляется к ответу
        )
        
    except Exception as e:
        logger.error(f"AI ошибка: {e}")
        await message.answer(
            f"❌ Ошибка: {str(e)}\nПопробуйте еще раз:",
            reply_markup=get_ai_keyboard()
        )


@router.message(Command("ai_status"))
async def ai_status(message: Message):
    """Проверка статуса"""
    if AI_AVAILABLE and assistant:
        try:
            connected = await assistant.test_connection()
            status = "✅ AI подключен и готов" if connected else "⚠️ AI не подключен"
        except:
            status = "⚠️ Ошибка проверки"
    else:
        status = "❌ AI не загружен"
    
    await message.answer(f"Статус AI: {status}")