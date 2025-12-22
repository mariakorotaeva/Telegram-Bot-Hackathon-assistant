from aiogram import Router, F, html
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from services.user_service import UserService
from .start import ROLES
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
    builder.button(text="👥 Команда", callback_data="participant_team_search")
    builder.button(text="❓ Частые вопросы", callback_data="participant_faq")
    builder.button(text="❓ Задать вопрос", callback_data="menu_ask_ai_question")
    builder.button(text="👤 Мой профиль", callback_data="menu_profile")
    
    builder.adjust(2, 2, 2)
    return builder.as_markup()

def get_organizer_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="📢 Сделать рассылку", callback_data="admin_broadcast")
    builder.button(text="✏️ Редактировать расписания", callback_data="admin_edit_schedule")
    builder.button(text="📊 Запустить опрос", callback_data="admin_create_poll")
    builder.button(text="👥 Управление задачами волонтеров", callback_data="admin_manage_tasks")
    builder.button(text="🔔 Управление уведомлениями", callback_data="menu_notifications")
    builder.button(text="❓ Задать вопрос", callback_data="menu_ask_ai_question")
    builder.button(text="👤 Мой профиль", callback_data="menu_profile")
    
    builder.adjust(2, 2, 2, 2)
    return builder.as_markup()

def get_mentor_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="🔔 Управление уведомлениями", callback_data="menu_notifications")
    builder.button(text="📋 Мои команды", callback_data="mentor_my_teams")
    builder.button(text="❓ Задать вопрос", callback_data="menu_ask_ai_question")
    builder.button(text="👤 Мой профиль", callback_data="menu_profile")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_volunteer_menu():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Расписание", callback_data="menu_schedule")
    builder.button(text="🔔 Управление уведомлениями", callback_data="menu_notifications")
    builder.button(text="📋 Мои задачи", callback_data="volunteer_tasks")
    builder.button(text="❓ Задать вопрос", callback_data="menu_ask_ai_question")
    builder.button(text="👤 Мой профиль", callback_data="menu_profile")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()

async def _show_menu(user_id: int, role: str, target: Message | CallbackQuery, is_callback: bool = False):
    user = await UserService().get_by_tg_id(user_id)
    full_name = user.full_name

    if role == "organizer":
        text = f"🎪 <b>Меню организатора</b>\n\nДобро пожаловать, {full_name}!"
        keyboard = get_organizer_menu()
    elif role == "mentor":
        text = f"🧠 <b>Меню ментора</b>\n\nДобро пожаловать, {full_name}!"
        keyboard = get_mentor_menu()
    elif role == "volunteer":
        text = f"🤝 <b>Меню волонтера</b>\n\nДобро пожаловать, {full_name}!"
        keyboard = get_volunteer_menu()
    else:
        text = f"👋 <b>Главное меню</b>\n\nДобро пожаловать, {full_name}!"
        keyboard = get_participant_menu()
    
    if is_callback:
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(F.text == "/menu")
async def show_menu_command(message: Message):
    user_id = int(message.from_user.id)
    user = await UserService().get_by_tg_id(user_id)

    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    
    role = user.role
    await _show_menu(user_id, role, message, is_callback=False)

@router.callback_query(F.data == "participant_faq")
async def show_faq(callback: CallbackQuery):
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)

    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    
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

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user_id = int(callback.from_user.id)
    user = await UserService().get_by_tg_id(user_id)

    if not user:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    
    await _show_menu(user_id, user.role, callback, is_callback=True)
    await callback.answer()