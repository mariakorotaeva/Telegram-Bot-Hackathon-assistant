"""
AI Assistant для хакатон-бота
Обработка вопросов пользователей через Ollama
"""
import os
import logging
import asyncio
from typing import Dict, Any
from aiogram import Router, F, html
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

# Импортируем нашу модель
try:
    from bot.models.ollama_handler import get_assistant
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bot.models.ollama_handler import get_assistant

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = Router()

class AIAssistantStates(StatesGroup):
    waiting_for_question = State()

class AIAssistant:
    def __init__(self):
        self.assistant = None
        self.is_available = False
        self._warmed_up = False
        
    async def initialize(self) -> bool:
        logger.info("Проверка подключения к Ollama...")
        
        try:
            self.assistant = get_assistant()
            self.is_available = await self.assistant.test_connection()
            if self.is_available:
                logger.info("✅ Ollama доступен!")
                await self._warm_up_model()
            else:
                logger.warning("⚠️ Ollama не доступен!")
            return self.is_available
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации AI ассистента: {e}")
            self.is_available = False
            return False
    
    async def _warm_up_model(self):
        if self._warmed_up or not self.is_available:
            return
        try:
            logger.info("Прогреваю модель...")
            warm_up_question = "Привет! Подтверди, что готов отвечать на вопросы о хакатоне."
            warm_up_result = await self.assistant.ask(warm_up_question)
            if warm_up_result['success']:
                self._warmed_up = True
                logger.info("✅ Модель успешно прогрета!")
            else:
                logger.warning("⚠️ Не удалось прогреть модель, но ассистент доступен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при прогреве модели: {e}")
    
    async def ask_question(self, question: str) -> Dict[str, Any]:
        if not self.is_available or not self.assistant:
            return {
                'success': False,
                'answer': '⚠️ AI ассистент временно недоступен.',
                'response_time': '0s',
                'model': 'Не доступен'
            }
        
        if len(question.strip()) < 3:
            return {
                'success': False,
                'answer': '📝 Пожалуйста, напишите вопрос более подробно.',
                'response_time': '0s',
                'model': 'Не доступен'
            }
        
        logger.info(f"📥 Вопрос: {question[:50]}...")
        try:
            result = await self.assistant.ask(question)
            if not result.get('success', False):
                result['answer'] = f"❌ Не удалось получить ответ.\n\n{result.get('answer', 'Попробуйте переформулировать вопрос.')}"
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при обработке вопроса: {e}")
            return {
                'success': False,
                'answer': '❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.',
                'response_time': '0s',
                'model': 'Ошибка'
            }
    
    async def get_standard_answer(self, category: str) -> Dict[str, Any]:
        questions_map = {
            "schedule": "Когда начало хакатона? Какое расписание? Какие сроки?",
            "topics": "Какие темы и направления хакатона? Что можно делать?",
            "teams": "Как формируются команды? Сколько человек должно быть?",
            "prizes": "Какие призы и критерии оценки проектов?",
            "rules": "Какие правила хакатона? Что можно и нельзя делать?",
            "contacts": "Как связаться с организаторами? Где получить помощь?"
        }
        if category not in questions_map:
            return await self.ask_question(category)
        return await self.ask_question(questions_map[category])

assistant = AIAssistant()

async def initialize_assistant() -> bool:
    logger.info("Инициализация AI ассистента...")
    try:
        result = await assistant.initialize()
        if result:
            logger.info("✅ AI ассистент готов к работе!")
        else:
            logger.warning("⚠️ AI ассистент не инициализирован")
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации: {e}")
        return False

@router.callback_query(F.data == "menu_ask_ai_question")
async def show_ai_assistant(callback: CallbackQuery, state: FSMContext):
    if not assistant.is_available:
        await callback.message.edit_text(
            "❌ <b>AI ассистент временно недоступен</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    welcome_text = (
        f"🤖 <b>Я -Лама, AI Ассистент Хакатона</b>\n\n"
        
        f"<b>Просто напишите ваш вопрос ниже!</b>"
    )
    
    await state.set_state(AIAssistantStates.waiting_for_question)
    await callback.message.edit_text(
        welcome_text,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.message(AIAssistantStates.waiting_for_question)
async def process_ai_question(message: Message, state: FSMContext):
    user_question = message.text.strip()
    if len(user_question) < 3:
        await message.answer(
            "📝 Пожалуйста, напишите вопрос более подробно (минимум 3 символа)."
        )
        return
    await message.bot.send_chat_action(message.chat.id, "typing")
    temp_msg = await message.answer("🧠 <b>Ищу ответ...</b>", parse_mode=ParseMode.HTML)
    result = await assistant.ask_question(user_question)
    try:
        await temp_msg.delete()
    except:
        pass
    if result['success']:
        response = (
            f"💬 <b>Ваш вопрос:</b> <i>{html.quote(user_question)}</i>\n\n"
            f"📝 <b>Ответ:</b>\n"
            f"{result['answer']}\n\n"
            f"<code>{result['response_time']}</code>"
        )
    else:
        response = (
            f"⚠️ <b>Не удалось получить ответ</b>\n\n"
            f"{result['answer']}"
        )
    
    await message.answer(response, parse_mode=ParseMode.HTML)
    await state.set_state(AIAssistantStates.waiting_for_question)

@router.callback_query(F.data == "ai_back_to_menu")
async def back_to_menu_from_ai(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from .menu import show_main_menu
    await show_main_menu(callback.message)
    await callback.answer()