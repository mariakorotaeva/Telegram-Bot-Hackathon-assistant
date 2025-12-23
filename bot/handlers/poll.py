from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, Poll, PollAnswer, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import asyncio
from typing import Dict, List, Set
import json

from .start import temp_users_storage
from .menu import back_to_menu_keyboard

from services.user_service import UserService
from services.poll_service import PollService

router = Router()

# Глобальное хранилище для опросов и их результатов
telegram_polls: Dict[str, Dict] = {}  # poll_id -> данные опроса
poll_messages: Dict[str, Dict] = {}  # poll_id -> {user_id: message_id}
poll_votes: Dict[str, Dict[str, int]] = {}  # poll_id -> {user_id: option_index}

class PollCreationStates(StatesGroup):
    waiting_for_question = State()
    waiting_for_options = State()
    waiting_for_final = State()

def get_poll_management_keyboard():
    """Клавиатура для управления опросами"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Создать новый опрос", callback_data="create_poll")
    builder.button(text="📊 Собрать результаты", callback_data="collect_results")
    builder.button(text="📋 Активные опросы", callback_data="view_active_polls")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()

def format_results_for_organizer(poll_data: Dict) -> str:
    """Форматирование результатов для организатора"""
    if not poll_data.get('results'):
        return "Пока нет голосов"
    
    results = poll_data['results']
    total_votes = sum(results.values())
    
    text = f"📊 <b>Результаты опроса</b>\n\n"
    text += f"<b>Вопрос:</b> {poll_data['question']}\n"
    text += f"<b>Всего голосов:</b> {total_votes}\n\n"
    
    if total_votes > 0:
        for i, option in enumerate(poll_data['options']):
            votes = results.get(str(i), 0)
            percentage = (votes / total_votes) * 100
            
            # Создаем прогресс-бар
            bar_length = 15
            filled = int(percentage / 100 * bar_length)
            progress_bar = "█" * filled + "░" * (bar_length - filled)
            
            text += f"<b>{i+1}. {option}</b>\n"
            text += f"{progress_bar} {votes} ({percentage:.1f}%)\n\n"
    
    return text

@router.callback_query(F.data == "admin_create_poll")
async def admin_poll_menu(callback: CallbackQuery):
    """Меню управления опросами для организатора"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    
    if user.role != "organizer":
        await callback.answer("❌ Эта функция доступна только организаторам", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📊 <b>Управление опросами Telegram</b>\n\n"
        "Здесь вы можете создавать единые опросы для всех участников.\n\n"
        "⚠️ <i>Примечание: Каждый пользователь получит свой опрос, "
        "но результаты будут собраны в единую статистику.</i>",
        reply_markup=get_poll_management_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "create_poll")
async def start_poll_creation(callback: CallbackQuery, state: FSMContext):
    """Начало создания опроса"""
    await state.set_state(PollCreationStates.waiting_for_question)
    
    await callback.message.edit_text(
        "📝 <b>Создание опроса Telegram</b>\n\n"
        "Введите вопрос для опроса:\n\n"
        "<i>Пример: Какой трек вам наиболее интересен?</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(PollCreationStates.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
    """Обработка вопроса опроса"""
    if len(message.text) > 300:
        await message.answer("❌ Вопрос слишком длинный. Максимум 300 символов.")
        return
    
    await state.update_data(question=message.text)
    await state.set_state(PollCreationStates.waiting_for_options)
    
    await message.answer(
        "✅ Вопрос сохранен!\n\n"
        "Теперь введите варианты ответов.\n"
        "Разделяйте варианты с новой строки:\n\n"
        "<i>Пример:\n"
        "Трек 1: Разработка\n"
        "Трек 2: Дизайн\n"
        "Трек 3: Маркетинг</i>\n\n"
        "Минимум 2 варианта, максимум 10.",
        parse_mode="HTML"
    )

@router.message(PollCreationStates.waiting_for_options)
async def process_options(message: Message, state: FSMContext):
    """Обработка вариантов ответов"""
    lines = [line.strip() for line in message.text.split('\n') if line.strip()]
    
    if len(lines) < 2:
        await message.answer("❌ Нужно как минимум 2 варианта ответа. Попробуйте снова.")
        return
    
    if len(lines) > 10:
        await message.answer("❌ Слишком много вариантов. Максимум 10. Попробуйте снова.")
        return
    
    # Проверяем длину каждого варианта
    for i, option in enumerate(lines):
        if len(option) > 100:
            await message.answer(f"❌ Вариант {i+1} слишком длинный. Максимум 100 символов.")
            return
    
    await state.update_data(options=lines)
    await state.set_state(PollCreationStates.waiting_for_final)
    
    # Формируем текст для предпросмотра
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(lines)])
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Создать и разослать", callback_data="send_polls_to_all")
    builder.button(text="❌ Отменить", callback_data="cancel_poll")
    builder.adjust(1)
    
    await message.answer(
        f"📋 <b>Предпросмотр опроса</b>\n\n"
        f"<b>Вопрос:</b> {(await state.get_data())['question']}\n\n"
        f"<b>Варианты ответов:</b>\n{options_text}\n\n"
        f"Этот опрос будет отправлен всем участникам через Telegram Poll.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "send_polls_to_all")
async def send_polls_to_all_users(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Отправка опроса всем пользователям"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if not user or user.role != "organizer":
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    data = await state.get_data()
    question = data.get("question")
    options = data.get("options", [])
    
    if len(options) < 2:
        await callback.answer("❌ Недостаточно вариантов ответа", show_alert=True)
        return
    
    # Генерируем уникальный ID для группы опросов
    poll_group_id = str(datetime.now().timestamp())
    
    # Сохраняем метаданные опроса
    telegram_polls[poll_group_id] = {
        "question": question,
        "options": options,
        "creator_id": user_id,
        "creator_name": user.full_name,
        "created_at": datetime.now().isoformat(),
        "sent_count": 0,
        "voted_count": 0,
        "results": {str(i): 0 for i in range(len(options))},
        "user_votes": {}  # user_id -> option_index
    }
    
    poll_messages[poll_group_id] = {}
    
    # Отправляем опрос всем пользователям
    sent_count = 0
    failed_count = 0
    
    for user in await UserService().get_all():
        try:
            # Отправляем нативный опрос Telegram
            sent_poll = await bot.send_poll(
                chat_id=user.telegram_id,
                question=question,
                options=options,
                is_anonymous=False,  # Не анонимный, чтобы видеть кто проголосовал
                type="regular",  # Обычный опрос (не викторина)
                allows_multiple_answers=False,
                protect_content=False
            )
            
            # Сохраняем ID сообщения с опросом
            poll_messages[poll_group_id][user.telegram_id] = sent_poll.message_id
            sent_count += 1
            
            # Небольшая задержка, чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"Не удалось отправить опрос пользователю {uid}: {e}")
            failed_count += 1
    
    # Обновляем счетчик отправленных опросов
    telegram_polls[poll_group_id]["sent_count"] = sent_count
    
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ <b>Опросы успешно отправлены!</b>\n\n"
        f"📊 <b>Статистика отправки:</b>\n"
        f"• Успешно: {sent_count} пользователей\n"
        f"• Не удалось: {failed_count} пользователей\n\n"
        f"<b>Вопрос:</b> {question}\n"
        f"<b>Вариантов:</b> {len(options)}\n"
        f"<b>ID группы опросов:</b> <code>{poll_group_id}</code>\n\n"
        f"<i>Результаты будут автоматически собираться по мере голосования.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Собрать результаты", callback_data=f"collect_results:{poll_group_id}")],
            [InlineKeyboardButton(text="🔙 В меню опросов", callback_data="admin_create_poll")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer, bot: Bot):
    """Обработка ответов на опросы Telegram"""
    user_id = str(poll_answer.user.id)
    
    # Находим, к какому опросу относится этот ответ
    for poll_group_id, poll_data in telegram_polls.items():
        if user_id in poll_messages.get(poll_group_id, {}):
            # Проверяем, голосовал ли уже пользователь
            if user_id in poll_data["user_votes"]:
                # Убираем старый голос
                old_vote = poll_data["user_votes"][user_id]
                poll_data["results"][str(old_vote)] = max(0, poll_data["results"][str(old_vote)] - 1)
            
            # Добавляем новый голос
            if poll_answer.option_ids:  # Пользователь может убрать голос
                option_index = poll_answer.option_ids[0]
                poll_data["user_votes"][user_id] = option_index
                poll_data["results"][str(option_index)] = poll_data["results"].get(str(option_index), 0) + 1
                poll_data["voted_count"] = len(poll_data["user_votes"])
            else:
                # Пользователь убрал голос
                if user_id in poll_data["user_votes"]:
                    del poll_data["user_votes"][user_id]
            
            # Обновляем хранилище
            telegram_polls[poll_group_id] = poll_data
            
            # Отправляем уведомление организатору (если нужно)
            creator_id = poll_data["creator_id"]
            if creator_id and poll_data["voted_count"] % 5 == 0:  # Каждые 5 голосов
                try:
                    await bot.send_message(
                        chat_id=int(creator_id),
                        text=f"📊 <b>Обновление по опросу</b>\n\n"
                             f"Проголосовало уже {poll_data['voted_count']} человек!",
                        parse_mode="HTML"
                    )
                except:
                    pass
            
            break

@router.callback_query(F.data.startswith("collect_results:"))
async def collect_poll_results(callback: CallbackQuery):
    """Сбор и отображение результатов опроса"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)

    poll_group_id = callback.data.split(":")[1]
    
    if not user or user.role != "organizer":
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    poll_data = telegram_polls.get(poll_group_id)
    if not poll_data:
        await callback.answer("❌ Опрос не найден", show_alert=True)
        return
    
    # Форматируем результаты
    results_text = format_results_for_organizer(poll_data)
    
    # Добавляем статистику
    stats = (
        f"\n📈 <b>Статистика:</b>\n"
        f"• Отправлено: {poll_data['sent_count']} пользователям\n"
        f"• Проголосовало: {poll_data['voted_count']} человек\n"
        f"• Процент участия: {poll_data['voted_count']/poll_data['sent_count']*100:.1f}%\n"
        f"• Создан: {poll_data['created_at'][:16].replace('T', ' ')}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить результаты", callback_data=f"collect_results:{poll_group_id}")
    builder.button(text="📥 Экспорт в JSON", callback_data=f"export_results:{poll_group_id}")
    builder.button(text="🔙 К списку опросов", callback_data="view_active_polls")
    builder.adjust(1)
    
    await callback.message.edit_text(
        results_text + stats,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("export_results:"))
async def export_poll_results(callback: CallbackQuery):
    """Экспорт результатов в текстовом виде"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)

    poll_group_id = callback.data.split(":")[1]
    
    if not user or user.role != "organizer":
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    poll_data = telegram_polls.get(poll_group_id)
    if not poll_data:
        await callback.answer("❌ Опрос не найден", show_alert=True)
        return
    
    # Создаем структуру для экспорта
    export_data = {
        "poll_id": poll_group_id,
        "question": poll_data["question"],
        "options": poll_data["options"],
        "created_at": poll_data["created_at"],
        "statistics": {
            "sent_count": poll_data["sent_count"],
            "voted_count": poll_data["voted_count"],
            "participation_rate": poll_data["voted_count"] / poll_data["sent_count"] if poll_data["sent_count"] > 0 else 0
        },
        "results": poll_data["results"],
        "voted_users": list(poll_data["user_votes"].keys())
    }
    
    # Конвертируем в JSON
    json_text = json.dumps(export_data, ensure_ascii=False, indent=2)
    
    # Отправляем как текстовый файл
    await callback.message.answer_document(
        document=("poll_results.json", json_text.encode()),
        caption=f"📊 Результаты опроса\nID: {poll_group_id}"
    )
    
    await callback.answer("✅ Результаты экспортированы")

@router.callback_query(F.data == "view_active_polls")
async def view_active_polls(callback: CallbackQuery):
    """Просмотр активных опросов"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь", show_alert=True)
        return
    
    user_role = user.role
    
    # Фильтруем опросы (для участников показываем только активные)
    active_polls_list = []
    for poll_id, poll_data in telegram_polls.items():
        if user_role == "organizer" or poll_data.get("is_active", True):
            active_polls_list.append((poll_id, poll_data))
    
    if not active_polls_list:
        await callback.message.edit_text(
            "📭 <b>Активных опросов нет</b>",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    polls_text = "📊 <b>Активные опросы:</b>\n\n"
    builder = InlineKeyboardBuilder()
    
    for poll_id, poll_data in active_polls_list[:10]:  # Ограничиваем 10 опросами
        polls_text += (
            f"• {poll_data['question'][:50]}...\n"
            f"  👤 Создал: {poll_data['creator_name']}\n"
            f"  🗳️ Проголосовало: {poll_data['voted_count']}/{poll_data['sent_count']}\n"
            f"  🕐 {poll_data['created_at'][:10]}\n\n"
        )
        
        if user_role == "organizer":
            builder.button(
                text=f"📊 {poll_data['question'][:20]}...",
                callback_data=f"collect_results:{poll_id}"
            )
    
    if user_role == "organizer":
        builder.button(text="🔙 В меню опросов", callback_data="admin_create_poll")
        builder.adjust(1)
        
        await callback.message.edit_text(
            polls_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            polls_text + "Для голосования проверьте свои личные сообщения с ботом.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer()

@router.callback_query(F.data == "collect_results")
async def collect_all_results(callback: CallbackQuery):
    """Меню сбора результатов"""
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if not user or user.role != "organizer":
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    if not telegram_polls:
        await callback.message.edit_text(
            "📭 <b>Опросов еще нет</b>\n\n"
            "Создайте первый опрос, чтобы видеть результаты.",
            reply_markup=get_poll_management_keyboard(),
            parse_mode="HTML"
        )
        return
    
    builder = InlineKeyboardBuilder()
    
    for poll_id, poll_data in list(telegram_polls.items())[:10]:
        builder.button(
            text=f"📊 {poll_data['question'][:30]}...",
            callback_data=f"collect_results:{poll_id}"
        )
    
    builder.button(text="🔙 Назад", callback_data="admin_create_poll")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📋 <b>Выберите опрос для просмотра результатов:</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_poll")
async def cancel_poll_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания опроса"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Создание опроса отменено.",
        reply_markup=get_poll_management_keyboard()
    )
    await callback.answer()