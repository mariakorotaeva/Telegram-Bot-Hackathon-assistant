from aiogram import Router, F, html
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from .start import temp_users_storage, ROLES

router = Router()

def get_participant_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="❓ Частые вопросы", callback_data="menu_faq")
    builder.button(text="👥 Поиск команды", callback_data="menu_team_search")
    builder.button(text="🔔 Управление уведомлениями", callback_data="menu_notifications")
    
    return builder.as_markup()

def get_organizer_menu():
    """Меню для организатора (админка)"""
    builder = InlineKeyboardBuilder()
    
    # Общие функции (как у участника)
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="❓ Частые вопросы", callback_data="menu_faq")
    
    # Админские функции
    builder.button(text="📢 Сделать рассылку", callback_data="admin_broadcast")
    builder.button(text="✏️ Редактировать расписание", callback_data="admin_edit_schedule")
    builder.button(text="📊 Запустить опрос", callback_data="admin_create_poll")
    
    builder.adjust(2, 2, 1)  # Расположение: 2-2-1
    return builder.as_markup()

def get_mentor_menu():
    """Меню для ментора = участник + специфичные кнопки"""
    builder = InlineKeyboardBuilder()
    
    # Базовые как у участника
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="❓ Частые вопросы", callback_data="menu_faq")
    builder.button(text="👥 Поиск команды", callback_data="menu_team_search")
    builder.button(text="🔔 Управление уведомлениями", callback_data="menu_notifications")
    builder.button(text="⚙️ Настройки", callback_data="menu_settings")
    
    # Специфичные для ментора
    builder.button(text="📋 Мои команды", callback_data="mentor_my_teams")
    builder.button(text="✅ Отметиться", callback_data="mentor_checkin")
    
    builder.adjust(2, 2, 1, 2)  # Расположение: 2-2-1-2
    return builder.as_markup()

def get_volunteer_menu():
    """Меню для волонтера = участник + специфичные кнопки"""
    builder = InlineKeyboardBuilder()
    
    # Базовые как у участника
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="❓ Частые вопросы", callback_data="menu_faq")
    builder.button(text="👥 Поиск команды", callback_data="menu_team_search")
    builder.button(text="🔔 Управление уведомлениями", callback_data="menu_notifications")
    builder.button(text="⚙️ Настройки", callback_data="menu_settings")
    
    # Специфичные для волонтера
    builder.button(text="📋 Мои задачи", callback_data="volunteer_tasks")
    builder.button(text="✅ Начать смену", callback_data="volunteer_shift_start")
    
    builder.adjust(2, 2, 1, 2)  # Расположение: 2-2-1-2
    return builder.as_markup()

# ==================== КОМАНДА /MENU ====================

@router.message(F.text == "/menu")
async def show_menu_command(message: Message):
    """Обработчик команды /menu"""
    user_id = str(message.from_user.id)
    
    if user_id not in temp_users_storage:
        await message.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return
    
    user_data = temp_users_storage[user_id]
    role = user_data.get("role", "participant")
    
    # Выбираем меню в зависимости от роли
    if role == "organizer":
        await message.answer(
            f"🎪 <b>Меню организатора</b>\n\n"
            f"Добро пожаловать, {user_data['full_name']}!",
            reply_markup=get_organizer_menu(),
            parse_mode="HTML"
        )
    elif role == "mentor":
        await message.answer(
            f"🧠 <b>Меню ментора</b>\n\n"
            f"Добро пожаловать, {user_data['full_name']}!",
            reply_markup=get_mentor_menu(),
            parse_mode="HTML"
        )
    elif role == "volunteer":
        await message.answer(
            f"🤝 <b>Меню волонтера</b>\n\n"
            f"Добро пожаловать, {user_data['full_name']}!",
            reply_markup=get_volunteer_menu(),
            parse_mode="HTML"
        )
    else:  # participant
        await message.answer(
            f"👋 <b>Главное меню</b>\n\n"
            f"Добро пожаловать, {user_data['full_name']}!",
            reply_markup=get_participant_menu(),
            parse_mode="HTML"
        )

# ==================== ОБРАБОТЧИКИ КНОПОК (ЗАГЛУШКИ) ====================

# Общие кнопки для всех
@router.callback_query(F.data == "menu_schedule")
async def show_schedule(callback: CallbackQuery):
    """Расписание - заглушка"""
    await callback.message.edit_text(
        "📅 <b>Расписание хакатона</b>\n\n"
        "Здесь будет расписание мероприятий.\n"
        "Пока что функция в разработке!",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_faq")
async def show_faq(callback: CallbackQuery):
    """FAQ - заглушка"""
    await callback.message.edit_text(
        "❓ <b>Часто задаваемые вопросы</b>\n\n"
        "1. <b>Когда начало?</b> - Скоро сообщим!\n"
        "2. <b>Где будет проходить?</b> - Онлайн\n"
        "3. <b>Как найти команду?</b> - Используйте поиск команды\n\n"
        "Полный список вопросов в разработке...",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_team_search")
async def team_search(callback: CallbackQuery):
    """Поиск команды - заглушка"""
    await callback.message.edit_text(
        "👥 <b>Поиск команды</b>\n\n"
        "Функции:\n"
        "• Подать заявку в команду\n"
        "• Заполнить анкету для поиска\n"
        "• Просмотреть анкеты других участников\n\n"
        "Эта функция скоро будет доступна!",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_notifications")
async def notifications_menu(callback: CallbackQuery):
    """Уведомления - заглушка"""
    await callback.message.edit_text(
        "🔔 <b>Управление уведомлениями</b>\n\n"
        "Настройте, о каких событиях получать уведомления:\n\n"
        "✅ Новости и анонсы\n"
        "✅ Напоминания о мероприятиях\n"
        "✅ Сообщения от команды\n"
        "✅ Деадлайны\n\n"
        "Настройки появятся позже!",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_settings")
async def settings_menu(callback: CallbackQuery):
    """Настройки - заглушка"""
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Доступные настройки:\n"
        "• Изменить часовой пояс\n"
        "• Сменить роль\n"
        "• Язык интерфейса\n\n"
        "Раздел в разработке!",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Специфичные кнопки ментора
@router.callback_query(F.data == "mentor_my_teams")
async def mentor_my_teams(callback: CallbackQuery):
    """Команды ментора - заглушка"""
    await callback.message.edit_text(
        "📋 <b>Мои команды</b>\n\n"
        "Команды, за которыми вы закреплены:\n"
        "1. Команда 'Котики' - проект: Чат-бот\n"
        "2. Команда 'Панды' - проект: ML модель\n\n"
        "Всего: 2 команды",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "mentor_checkin")
async def mentor_checkin(callback: CallbackQuery):
    """Отметка ментора - заглушка"""
    await callback.message.edit_text(
        "✅ <b>Отметка о присутствии</b>\n\n"
        "Вы отметились!\n"
        "Спасибо что помогаете участникам!",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Специфичные кнопки волонтера
@router.callback_query(F.data == "volunteer_tasks")
async def volunteer_tasks(callback: CallbackQuery):
    """Задачи волонтера - заглушка"""
    await callback.message.edit_text(
        "📋 <b>Мои задачи на смену</b>\n\n"
        "1. Раздать воду участникам (10:00) ✅\n"
        "2. Проверить микрофоны в зале (11:00) ⏳\n"
        "3. Помочь с подключением (12:00) ❌\n"
        "4. Собрать фидбэк (18:00) ❌\n\n"
        "✅ - сделано, ⏳ - сейчас, ❌ - ждет",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "volunteer_shift_start")
async def volunteer_shift_start(callback: CallbackQuery):
    """Смена волонтера - заглушка"""
    await callback.message.edit_text(
        "🕐 <b>Начало смены</b>\n\n"
        "Смена начата!\n"
        "Удачи в помощи участникам! ✨\n\n"
        "Не забудьте отметить конец смены.",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Админские кнопки
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery):
    """Рассылка - заглушка"""
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Отправить сообщение:\n"
        "• Всем участникам\n"
        "• По ролям (участники/менторы/волонтеры)\n"
        "• Конкретным людям\n\n"
        "Админ-панель в разработке!",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_edit_schedule")
async def admin_edit_schedule(callback: CallbackQuery):
    """Редактирование расписания - заглушка"""
    await callback.message.edit_text(
        "✏️ <b>Редактирование расписания</b>\n\n"
        "Здесь можно:\n"
        "• Добавить новое мероприятие\n"
        "• Изменить существующее\n"
        "• Удалить мероприятие\n"
        "• Импортировать из Google Sheets\n\n"
        "Функция появится позже!",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_create_poll")
async def admin_create_poll(callback: CallbackQuery):
    """Создание опроса - заглушка"""
    await callback.message.edit_text(
        "📊 <b>Запуск опроса</b>\n\n"
        "Создать опрос для:\n"
        "• Всех участников\n"
        "• Определенной роли\n"
        "• Конкретной группы\n\n"
        "Скоро будет реализовано!",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def back_to_menu_keyboard():
    """Клавиатура с кнопкой 'Назад'"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
        ]
    )
    return keyboard

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    # Просто вызываем команду /menu
    await show_menu_command(callback.message)
    await callback.answer()