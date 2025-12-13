from aiogram import Router, F, html
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from .start import temp_users_storage, ROLES
from .broadcast import BroadcastStates

router = Router()

def back_to_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    return builder.as_markup()

def get_participant_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="🔔 Управление уведомлениями", callback_data="menu_notifications")
    builder.button(text="👥 Поиск команды", callback_data="participant_team_search")
    builder.button(text="❓ Частые вопросы", callback_data="participant_faq")
    
    builder.adjust(2, 2)
    return builder.as_markup()

def get_organizer_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="📢 Сделать рассылку", callback_data="admin_broadcast")
    builder.button(text="✏️ Редактировать расписания", callback_data="admin_edit_schedule")
    builder.button(text="📊 Запустить опрос", callback_data="admin_create_poll")
    
    builder.adjust(2, 2)
    return builder.as_markup()

def get_mentor_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="🔔 Управление уведомлениями", callback_data="menu_notifications")
    builder.button(text="📋 Мои команды", callback_data="mentor_my_teams")
    builder.button(text="🤝 Назначить встречу", callback_data="mentor_set_meeting")
    
    builder.adjust(2, 2)
    return builder.as_markup()

def get_volunteer_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="🔔 Управление уведомлениями", callback_data="menu_notifications")
    builder.button(text="📋 Мои задачи", callback_data="volunteer_tasks")
    
    builder.adjust(2, 1)
    return builder.as_markup()

async def _show_menu(user_id: str, target: Message | CallbackQuery, is_callback: bool = False):
    user_data = temp_users_storage[user_id]
    role = user_data["role"]
    
    if role == "organizer":
        text = f"🎪 <b>Меню организатора</b>\n\nДобро пожаловать, {user_data['full_name']}!"
        keyboard = get_organizer_menu()
    elif role == "mentor":
        text = f"🧠 <b>Меню ментора</b>\n\nДобро пожаловать, {user_data['full_name']}!"
        keyboard = get_mentor_menu()
    elif role == "volunteer":
        text = f"🤝 <b>Меню волонтера</b>\n\nДобро пожаловать, {user_data['full_name']}!"
        keyboard = get_volunteer_menu()
    else:
        text = f"👋 <b>Главное меню</b>\n\nДобро пожаловать, {user_data['full_name']}!"
        keyboard = get_participant_menu()
    
    if is_callback:
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(F.text == "/menu")
async def show_menu_command(message: Message):
    user_id = str(message.from_user.id)
    
    if user_id not in temp_users_storage:
        await message.answer("❌ Сначала зарегистрируйся с помощью /start")
        return
    
    await _show_menu(user_id, message, is_callback=False)

@router.callback_query(F.data == "menu_notifications")
async def notifications_menu(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    user_data = temp_users_storage.get(user_id, {})
    role = user_data.get("role", "participant")
    
    await callback.message.edit_text(
        f"🔔 <b>Управление уведомлениями</b>\n\n"
        "Заглушка",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "participant_faq")
async def show_faq(callback: CallbackQuery):
    from bot.services.faq_service import faq_service
    categories = faq_service.get_categories()
   
    if not categories:
        await callback.message.edit_text(
            "📚 FAQ временно недоступен. Попробуйте позже.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    builder = InlineKeyboardBuilder()
   
    category_names = {
        "general": "📋 Общие вопросы",
        "registration": "📝 Регистрация",
        "technical": "⚙️ Технические вопросы"
    }
   
    for category in categories:
        button_text = category_names.get(category, category.capitalize())
        builder.button(
            text=button_text,
            callback_data=f"faq_category:{category}"
        )
   
    builder.button(
        text="📚 Все вопросы",
        callback_data="faq_all"
    )
   
    builder.button(
        text="⬅️ Назад в меню",
        callback_data="back_to_menu"
    )
    builder.adjust(1)
   
    await callback.message.edit_text(
        "📚 <b>Часто задаваемые вопросы</b>\n\n"
        "Выберите категорию:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "participant_team_search")
async def team_search(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>Поиск команды</b>\n\n"
        "Заглушка",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "mentor_my_teams")
async def mentor_my_teams(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 <b>Мои команды</b>\n\n"
        "Заглушка",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "mentor_set_meeting")
async def mentor_set_meeting(callback: CallbackQuery):
    await callback.message.edit_text(
        "🤝 <b>Назначить встречу с командой</b>\n\n"
        "Заглушка",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_create_poll")
async def admin_create_poll(callback: CallbackQuery):
    await callback.message.edit_text(
        "📊 <b>Запуск опроса</b>\n\n"
        "Заглушка",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if user_id not in temp_users_storage:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    
    await _show_menu(user_id, callback, is_callback=True)
    await callback.answer()