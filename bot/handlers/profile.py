from aiogram import Router, F, html
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .start import temp_users_storage, ROLES, TIMEZONES, validate_name
from .menu import router as menu_router

router = Router()

class ProfileEditStates(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_timezone = State()
    waiting_for_new_role = State()

def get_profile_keyboard(user_data):
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✏️ Изменить ФИО", callback_data="profile_edit_name")
    builder.button(text="✏️ Изменить часовой пояс", callback_data="profile_edit_timezone")
    builder.button(text="✏️ Изменить роль", callback_data="profile_edit_role")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    
    builder.adjust(2, 2)
    return builder.as_markup()

def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Отменить", callback_data="profile_cancel")
    return builder.as_markup()

@router.callback_query(F.data == "menu_profile")
async def show_profile(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if user_id not in temp_users_storage:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    
    user_data = temp_users_storage[user_id]
    
    profile_text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"<b>ФИО:</b> {html.quote(user_data['full_name'])}\n"
        f"<b>Роль:</b> {ROLES.get(user_data['role'], 'Неизвестно')}\n"
        f"<b>Часовой пояс:</b> {TIMEZONES.get(user_data['timezone'], 'Неизвестно')}\n"
        f"<b>Telegram ID:</b> {user_id}\n"
        f"<b>Username:</b> @{user_data.get('username', 'отсутствует')}"
    )
    
    await callback.message.edit_text(
        profile_text,
        reply_markup=get_profile_keyboard(user_data),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "profile_edit_name")
async def start_edit_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileEditStates.waiting_for_new_name)
    
    await callback.message.edit_text(
        "✏️ <b>Изменение ФИО</b>\n\n"
        "Введите ваше новое ФИО:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ProfileEditStates.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    user_id = str(message.from_user.id)
    
    is_valid, error_message = validate_name(new_name)
    if not is_valid:
        await message.answer(error_message)
        return
    
    temp_users_storage[user_id]["full_name"] = new_name
    
    await state.clear()
    
    await message.answer(
        f"✅ <b>ФИО успешно изменено!</b>\n\n"
        f"Теперь вас зовут: <b>{html.quote(new_name)}</b>\n\n"
        "Используйте /menu для возврата в главное меню.",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "profile_edit_timezone")
async def start_edit_timezone(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    
    for tz_key, tz_name in TIMEZONES.items():
        builder.button(text=tz_name, callback_data=f"profile_tz_{tz_key}")
    
    builder.button(text="Отменить", callback_data="profile_cancel")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "🌍 <b>Изменение часового пояса</b>\n\n"
        "Выберите ваш новый часовой пояс:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("profile_tz_"))
async def process_new_timezone(callback: CallbackQuery):
    tz_key = callback.data.replace("profile_tz_", "")
    user_id = str(callback.from_user.id)
    
    if tz_key not in TIMEZONES:
        await callback.answer("❌ Неверный часовой пояс!", show_alert=True)
        return
    
    temp_users_storage[user_id]["timezone"] = tz_key
    
    await callback.message.edit_text(
        f"✅ <b>Часовой пояс успешно изменен!</b>\n\n"
        f"Теперь ваш часовой пояс: <b>{TIMEZONES[tz_key]}</b>\n\n"
        "Используйте /menu для возврата в главное меню.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "profile_edit_role")
async def start_edit_role(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    
    for role_key, role_name in ROLES.items():
        builder.button(text=role_name, callback_data=f"profile_role_{role_key}")
    
    builder.button(text="❌ Отменить", callback_data="profile_cancel")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "🔄 <b>Изменение роли</b>\n\n"
        "Выберите вашу новую роль:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("profile_role_"))
async def process_new_role(callback: CallbackQuery):
    role_key = callback.data.replace("profile_role_", "")
    user_id = str(callback.from_user.id)
    
    if role_key not in ROLES:
        await callback.answer("❌ Неверная роль!", show_alert=True)
        return
    
    temp_users_storage[user_id]["role"] = role_key
    
    await callback.message.edit_text(
    f"✅ <b>Роль успешно изменена!</b>\n\n"
    f"Теперь ваша роль: <b>{ROLES[role_key]}</b>\n\n"
    "Используйте /menu для возврата в главное меню.",
    parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "profile_cancel")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    user_id = str(callback.from_user.id)
    if user_id in temp_users_storage:
        user_data = temp_users_storage[user_id]
        
        profile_text = (
            f"👤 <b>Ваш профиль</b>\n\n"
            f"<b>ФИО:</b> {html.quote(user_data['full_name'])}\n"
            f"<b>Роль:</b> {ROLES.get(user_data['role'], 'Неизвестно')}\n"
            f"<b>Часовой пояс:</b> {TIMEZONES.get(user_data['timezone'], 'Неизвестно')}\n"
            f"<b>Telegram ID:</b> {user_id}\n"
            f"<b>Username:</b> @{user_data.get('username', 'отсутствует')}"
        )
        
        await callback.message.edit_text(
            profile_text,
            reply_markup=get_profile_keyboard(user_data),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "❌ Профиль не найден!\n\n"
            "Используйте /start для регистрации.",
            parse_mode="HTML"
        )
    
    await callback.answer()