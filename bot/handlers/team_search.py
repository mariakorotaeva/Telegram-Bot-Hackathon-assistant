from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

# Временное хранилище анкет участников (в реальном проекте заменить на БД)
team_search_storage = {
    # Пример структуры:
    # "user_id": {
    #     "full_name": "Иван Иванов",
    #     "role": "участник",
    #     "skills": "Python, Django, React",
    #     "looking_for": "Backend разработчик",
    #     "project_idea": "Хочу сделать приложение для...",
    #     "contact": "@username"
    # }
}

# Состояния для заполнения анкеты
class TeamSearchStates(StatesGroup):
    waiting_for_skills = State()
    waiting_for_looking_for = State()
    waiting_for_project_idea = State()
    waiting_for_contact = State()

# Меню поиска команды
def get_team_search_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📝 Создать анкету", callback_data="team_create_profile")
    builder.button(text="👀 Найти команду/участников", callback_data="team_find")
    builder.button(text="📋 Моя анкета", callback_data="team_my_profile")
    builder.button(text="✏️ Редактировать анкету", callback_data="team_edit_profile")
    builder.button(text="🗑️ Удалить анкету", callback_data="team_delete_profile")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    
    builder.adjust(1)
    return builder.as_markup()

# Хендлер для входа в раздел поиска команды
@router.callback_query(F.data == "participant_team_search")
async def team_search_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>Поиск команды</b>\n\n"
        "Здесь вы можете:\n"
        "• Создать анкету для поиска команды\n"
        "• Найти участников или команды\n"
        "• Просмотреть и редактировать свою анкету\n\n"
        "<i>Выберите действие:</i>",
        reply_markup=get_team_search_menu(),
        parse_mode="HTML"
    )
    await callback.answer()

# Создание анкеты - шаг 1
@router.callback_query(F.data == "team_create_profile")
async def start_create_profile(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    
    # Проверяем, есть ли уже анкета
    if user_id in team_search_storage:
        await callback.message.edit_text(
            "⚠️ У вас уже есть активная анкета!\n"
            "Хотите отредактировать её?",
            reply_markup=InlineKeyboardBuilder()
                .button(text="✏️ Редактировать", callback_data="team_edit_profile")
                .button(text="❌ Отмена", callback_data="participant_team_search")
                .adjust(2)
                .as_markup()
        )
        await callback.answer()
        return
    
    await state.set_state(TeamSearchStates.waiting_for_skills)
    await callback.message.edit_text(
        "📝 <b>Создание анкеты</b>\n\n"
        "Шаг 1/4\n"
        "Расскажите о своих навыках и технологиях, которыми владеете:\n\n"
        "<i>Пример: Python, Django, React, PostgreSQL, Figma</i>",
        parse_mode="HTML"
    )
    await callback.answer()

# Получение навыков
@router.message(TeamSearchStates.waiting_for_skills)
async def process_skills(message: Message, state: FSMContext):
    await state.update_data(skills=message.text)
    await state.set_state(TeamSearchStates.waiting_for_looking_for)
    
    await message.answer(
        "🎯 <b>Шаг 2/4</b>\n\n"
        "Какую роль в команде вы ищете?\n\n"
        "<i>Пример: Backend разработчик, Дизайнер, Project Manager, Fullstack разработчик</i>",
        parse_mode="HTML"
    )

# Получение роли
@router.message(TeamSearchStates.waiting_for_looking_for)
async def process_looking_for(message: Message, state: FSMContext):
    await state.update_data(looking_for=message.text)
    await state.set_state(TeamSearchStates.waiting_for_project_idea)
    
    await message.answer(
        "💡 <b>Шаг 3/4</b>\n\n"
        "Есть ли у вас идея проекта? Если да, кратко опишите:\n\n"
        "<i>Пример: Хочу сделать мобильное приложение для отслеживания экологических привычек с геймификацией</i>\n"
        "<i>Или напишите 'Пока нет идей'</i>",
        parse_mode="HTML"
    )

# Получение идеи проекта
@router.message(TeamSearchStates.waiting_for_project_idea)
async def process_project_idea(message: Message, state: FSMContext):
    await state.update_data(project_idea=message.text)
    await state.set_state(TeamSearchStates.waiting_for_contact)
    
    await message.answer(
        "📞 <b>Шаг 4/4</b>\n\n"
        "Как с вами связаться?\n\n"
        "<i>Пример: Telegram @username, Email: example@mail.ru, Discord: username#1234</i>",
        parse_mode="HTML"
    )

# Получение контактов и сохранение анкеты
@router.message(TeamSearchStates.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    from .start import temp_users_storage
    
    user_id = str(message.from_user.id)
    
    if user_id not in temp_users_storage:
        await message.answer("❌ Ошибка: сначала завершите регистрацию через /start")
        await state.clear()
        return
    
    # Получаем все данные
    data = await state.get_data()
    user_data = temp_users_storage[user_id]
    
    # Сохраняем анкету
    team_search_storage[user_id] = {
        "full_name": user_data["full_name"],
        "role": user_data["role"],
        "timezone": user_data.get("timezone", "Не указан"),
        "skills": data.get("skills", ""),
        "looking_for": data.get("looking_for", ""),
        "project_idea": data.get("project_idea", ""),
        "contact": message.text,
        "created_at": message.date.strftime("%d.%m.%Y %H:%M")
    }
    
    # Формируем сводку
    profile_text = (
        "✅ <b>Анкета успешно создана!</b>\n\n"
        f"<b>Имя:</b> {user_data['full_name']}\n"
        f"<b>Роль:</b> {user_data['role']}\n"
        f"<b>Навыки:</b> {data.get('skills', '')}\n"
        f"<b>Ищу роль:</b> {data.get('looking_for', '')}\n"
        f"<b>Идея проекта:</b> {data.get('project_idea', '')}\n"
        f"<b>Контакты:</b> {message.text}\n\n"
        "Теперь другие участники смогут увидеть вашу анкету!"
    )
    
    await message.answer(profile_text, parse_mode="HTML")
    
    # Показываем меню поиска команды
    builder = InlineKeyboardBuilder()
    builder.button(text="👀 Смотреть анкеты других", callback_data="team_find")
    builder.button(text="📋 Моя анкета", callback_data="team_my_profile")
    builder.button(text="🔙 В меню поиска", callback_data="participant_team_search")
    builder.adjust(1)
    
    await message.answer("Что дальше?", reply_markup=builder.as_markup())
    await state.clear()

# Просмотр своей анкеты
@router.callback_query(F.data == "team_my_profile")
async def show_my_profile(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if user_id not in team_search_storage:
        await callback.message.edit_text(
            "❌ У вас ещё нет анкеты!\n"
            "Создайте анкету, чтобы другие участники могли вас найти.",
            reply_markup=InlineKeyboardBuilder()
                .button(text="📝 Создать анкету", callback_data="team_create_profile")
                .button(text="🔙 Назад", callback_data="participant_team_search")
                .adjust(1)
                .as_markup()
        )
        await callback.answer()
        return
    
    profile = team_search_storage[user_id]
    
    profile_text = (
        "📋 <b>Ваша анкета</b>\n\n"
        f"<b>Имя:</b> {profile['full_name']}\n"
        f"<b>Роль:</b> {profile['role']}\n"
        f"<b>Часовой пояс:</b> {profile['timezone']}\n"
        f"<b>Навыки:</b> {profile['skills']}\n"
        f"<b>Ищу роль:</b> {profile['looking_for']}\n"
        f"<b>Идея проекта:</b> {profile['project_idea']}\n"
        f"<b>Контакты:</b> {profile['contact']}\n"
        f"<b>Создана:</b> {profile['created_at']}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data="team_edit_profile")
    builder.button(text="🗑️ Удалить", callback_data="team_delete_profile")
    builder.button(text="🔙 Назад", callback_data="participant_team_search")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(profile_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

# Поиск анкет других участников
@router.callback_query(F.data == "team_find")
async def find_teams(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    # Фильтруем анкеты других пользователей
    other_profiles = {
        uid: profile for uid, profile in team_search_storage.items() 
        if uid != user_id
    }
    
    if not other_profiles:
        await callback.message.edit_text(
            "👀 <b>Поиск участников</b>\n\n"
            "Пока нет активных анкет других участников.\n"
            "Будьте первым, кто создаст анкету!",
            reply_markup=InlineKeyboardBuilder()
                .button(text="📝 Создать анкету", callback_data="team_create_profile")
                .button(text="🔄 Обновить", callback_data="team_find")
                .button(text="🔙 Назад", callback_data="participant_team_search")
                .adjust(2, 1)
                .as_markup()
        )
        await callback.answer()
        return
    
    # Преобразуем в список для пагинации
    profiles_list = list(other_profiles.items())
    
    await show_profile_page(callback, profiles_list, 0)
    await callback.answer()

# Показать страницу с анкетой
async def show_profile_page(callback: CallbackQuery, profiles_list: list, page: int):
    if page >= len(profiles_list):
        page = 0
    elif page < 0:
        page = len(profiles_list) - 1
    
    user_id, profile = profiles_list[page]
    
    profile_text = (
        f"👤 <b>Анкета {page + 1} из {len(profiles_list)}</b>\n\n"
        f"<b>Имя:</b> {profile['full_name']}\n"
        f"<b>Роль:</b> {profile['role']}\n"
        f"<b>Часовой пояс:</b> {profile['timezone']}\n"
        f"<b>Навыки:</b> {profile['skills']}\n"
        f"<b>Ищет роль:</b> {profile['looking_for']}\n"
        f"<b>Идея проекта:</b> {profile['project_idea']}\n"
        f"<b>Контакты:</b> {profile['contact']}\n"
        f"<b>Создана:</b> {profile['created_at']}"
    )
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки навигации
    if len(profiles_list) > 1:
        if page > 0:
            builder.button(text="⬅️ Назад", callback_data=f"team_profile_page:{page-1}")
        if page < len(profiles_list) - 1:
            builder.button(text="Вперед ➡️", callback_data=f"team_profile_page:{page+1}")
    
    builder.button(text="📝 Создать свою анкету", callback_data="team_create_profile")
    builder.button(text="🔄 Обновить список", callback_data="team_find")
    builder.button(text="🔙 В меню поиска", callback_data="participant_team_search")
    
    if len(profiles_list) > 1:
        builder.adjust(2, 2, 1)
    else:
        builder.adjust(1)
    
    await callback.message.edit_text(profile_text, reply_markup=builder.as_markup(), parse_mode="HTML")

# Пагинация по анкетам
@router.callback_query(F.data.startswith("team_profile_page:"))
async def handle_profile_page(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    # Получаем все анкеты других пользователей
    other_profiles = {
        uid: profile for uid, profile in team_search_storage.items() 
        if uid != user_id
    }
    
    if not other_profiles:
        await callback.answer("Нет доступных анкет", show_alert=True)
        return
    
    profiles_list = list(other_profiles.items())
    
    # Получаем номер страницы
    page = int(callback.data.split(":")[1])
    
    await show_profile_page(callback, profiles_list, page)
    await callback.answer()

# Редактирование анкеты
@router.callback_query(F.data == "team_edit_profile")
async def edit_profile(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if user_id not in team_search_storage:
        await callback.answer("У вас нет анкеты для редактирования", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    
    # Предлагаем что редактировать
    builder.button(text="🎯 Навыки", callback_data="team_edit:skills")
    builder.button(text="🔍 Ищу роль", callback_data="team_edit:looking_for")
    builder.button(text="💡 Идея проекта", callback_data="team_edit:project_idea")
    builder.button(text="📞 Контакты", callback_data="team_edit:contact")
    builder.button(text="❌ Отмена", callback_data="team_my_profile")
    
    builder.adjust(1)
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование анкеты</b>\n\n"
        "Выберите, что хотите изменить:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

# Удаление анкеты
@router.callback_query(F.data == "team_delete_profile")
async def delete_profile(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data="team_delete_confirm")
    builder.button(text="❌ Нет, отменить", callback_data="team_my_profile")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "🗑️ <b>Удаление анкеты</b>\n\n"
        "Вы уверены, что хотите удалить свою анкету?\n"
        "Это действие нельзя отменить.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "team_delete_confirm")
async def delete_profile_confirm(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if user_id in team_search_storage:
        del team_search_storage[user_id]
    
    await callback.message.edit_text(
        "✅ <b>Анкета удалена</b>\n\n"
        "Ваша анкета успешно удалена.",
        reply_markup=InlineKeyboardBuilder()
            .button(text="📝 Создать новую анкету", callback_data="team_create_profile")
            .button(text="🔙 В меню поиска", callback_data="participant_team_search")
            .adjust(1)
            .as_markup()
    )
    await callback.answer()