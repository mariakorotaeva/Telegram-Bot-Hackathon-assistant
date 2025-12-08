from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

router = Router()

def get_participant_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="Расписание", callback_data="menu_schedule")
    builder.button(text="Частые вопросы", callback_data="menu_faq")
    builder.button(text="Поиск команды", callback_data="menu_team_search")
    builder.button(text="Управление уведомлениями", callback_data="menu_notifications")
    builder.button(text="Настройки", callback_data="menu_settings")
    builder.button(text="Добавить ссылку/фото/видео", callback_data="menu_add_content")
    
    builder.adjust(2, 2, 1, 1)  # Расположение кнопок: 2 в первом ряду, 2 во втором, 1 в третьем, 1 в четвертом
    return builder.as_markup()

def get_organizer_menu():
    """Меню для организатора (админка)"""
    builder = InlineKeyboardBuilder()
    
    # Общие функции
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="❓ Частые вопросы", callback_data="menu_faq")
    
    # Админские функции
    builder.button(text="📢 Сделать рассылку", callback_data="admin_broadcast")
    builder.button(text="✏️ Редактировать расписание", callback_data="admin_edit_schedule")
    builder.button(text="📊 Запустить опрос", callback_data="admin_create_poll")
    builder.button(text="👥 Просмотр участников", callback_data="admin_view_users")
    
    builder.adjust(2, 2, 2)  # 2 кнопки в каждом ряду
    return builder.as_markup()

# ==================== КОМАНДА /MENU ====================

@router.message(F.text == "/menu")
async def show_menu(message: Message):
    """Показать главное меню (пока заглушка, потом подключим БД)"""
    # TODO: Здесь нужно будет получать роль пользователя из БД
    # Пока для теста - определяем по тексту
    user_id = str(message.from_user.id)
    
    # Временная логика: если в имени есть "org" или "админ" - показываем админку
    # ПОТОМ ЗАМЕНИШЬ на проверку из БД!
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""
    
    if "org" in username.lower() or "org" in full_name.lower() or "админ" in full_name.lower():
        # Показываем меню организатора
        await message.answer(
            "🎪 <b>Меню организатора</b>\n\n"
            "Выберите действие:",
            reply_markup=get_organizer_menu(),
            parse_mode="HTML"
        )
    else:
        # Показываем меню участника
        await message.answer(
            "👋 <b>Главное меню</b>\n\n"
            "Выберите действие:",
            reply_markup=get_participant_menu(),
            parse_mode="HTML"
        )

# ==================== ОБРАБОТЧИКИ КНОПОК УЧАСТНИКА ====================

@router.callback_query(F.data == "menu_schedule")
async def show_schedule(callback: CallbackQuery):
    """Расписание (заглушка)"""
    await callback.message.edit_text(
        "📅 <b>Расписание хакатона</b>\n\n"
        "Здесь будет расписание мероприятий.\n"
        "Пока что функция в разработке!",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_faq")
async def show_faq(callback: CallbackQuery):
    """Частые вопросы (заглушка)"""
    await callback.message.edit_text(
        "❓ <b>Часто задаваемые вопросы</b>\n\n"
        "1. <b>Когда начало?</b> - Скоро сообщим!\n"
        "2. <b>Где будет проходить?</b> - Онлайн\n"
        "3. <b>Как найти команду?</b> - Используйте поиск команды\n\n"
        "Полный список вопросов в разработке...",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_team_search")
async def team_search(callback: CallbackQuery):
    """Поиск команды (заглушка)"""
    await callback.message.edit_text(
        "👥 <b>Поиск команды</b>\n\n"
        "Функции:\n"
        "• Подать заявку в команду\n"
        "• Заполнить анкету для поиска\n"
        "• Просмотреть анкеты других участников\n\n"
        "Эта функция скоро будет доступна!",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_notifications")
async def notifications_menu(callback: CallbackQuery):
    """Управление уведомлениями (заглушка)"""
    await callback.message.edit_text(
        "🔔 <b>Управление уведомлениями</b>\n\n"
        "Настройте, о каких событиях получать уведомления:\n\n"
        "✅ Новости и анонсы\n"
        "✅ Напоминания о мероприятиях\n"
        "✅ Сообщения от команды\n"
        "✅ Деадлайны\n\n"
        "Настройки появятся позже!",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_settings")
async def settings_menu(callback: CallbackQuery):
    """Настройки (заглушка)"""
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Доступные настройки:\n"
        "• Изменить часовой пояс\n"
        "• Сменить роль\n"
        "• Язык интерфейса\n\n"
        "Раздел в разработке!",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_add_content")
async def add_content(callback: CallbackQuery):
    """Добавить контент (заглушка)"""
    await callback.message.edit_text(
        "📎 <b>Добавить ссылку/фото/видео</b>\n\n"
        "Отправьте ссылку, фото или видео, и мы добавим его в общую галерею хакатона!\n\n"
        "Функция скоро будет доступна!",
        parse_mode="HTML"
    )
    await callback.answer()

# ==================== ОБРАБОТЧИКИ КНОПОК ОРГАНИЗАТОРА ====================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery):
    """Рассылка (заглушка)"""
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Отправить сообщение:\n"
        "• Всем участникам\n"
        "• По ролям (участники/менторы/волонтеры)\n"
        "• Конкретным людям\n\n"
        "Админ-панель в разработке!",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_edit_schedule")
async def admin_edit_schedule(callback: CallbackQuery):
    """Редактирование расписания (заглушка)"""
    await callback.message.edit_text(
        "✏️ <b>Редактирование расписания</b>\n\n"
        "Здесь можно:\n"
        "• Добавить новое мероприятие\n"
        "• Изменить существующее\n"
        "• Удалить мероприятие\n"
        "• Импортировать из Google Sheets\n\n"
        "Функция появится позже!",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_create_poll")
async def admin_create_poll(callback: CallbackQuery):
    """Создание опроса (заглушка)"""
    await callback.message.edit_text(
        "📊 <b>Запуск опроса</b>\n\n"
        "Создать опрос для:\n"
        "• Всех участников\n"
        "• Определенной роли\n"
        "• Конкретной группы\n\n"
        "Скоро будет реализовано!",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_view_users")
async def admin_view_users(callback: CallbackQuery):
    """Просмотр участников"""
    await callback.message.edit_text(
        "👥 <b>Просмотр участников</b>\n\n"
        "Используйте команду /users для просмотра списка зарегистрированных пользователей.",
        parse_mode="HTML"
    )
    await callback.answer()

# ==================== КНОПКА "НАЗАД" ====================

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    # Вызываем ту же функцию что и /menu
    await show_menu(callback.message)
    await callback.answer()