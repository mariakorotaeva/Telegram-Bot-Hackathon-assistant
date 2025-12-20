from aiogram import Router, F, html
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Tuple, Optional

from services.user_service import UserService

router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_role = State()
    waiting_for_timezone = State()

temp_users_storage = {} #потом надо к бд подключится

ROLES = {
    "participant": "👤Участник",
    "organizer": "🎪 Организатор", 
    "mentor": "🧠 Ментор",
    "volunteer": "🤝 Волонтёр"
}

TIMEZONES = {
    "UTC+3": "Москва (UTC+3)",
    "UTC+4": "Самара (UTC+4)", 
    "UTC+5": "Екатеринбург (UTC+5)",
    "UTC+6": "Омск (UTC+6)",
    "UTC+7": "Красноярск (UTC+7)",
    "UTC+8": "Иркутск (UTC+8)",
    "UTC+9": "Якутск (UTC+9)",
    "UTC+10": "Владивосток (UTC+10)"
}

def validate_name(name: str) -> Tuple[bool, Optional[str]]:
    name = name.strip()
    
    if len(name) < 3:
        return False, "❌ Что-то не похоже на ФИО! Попробуй ещё раз."
    
    if any(char.isdigit() for char in name):
        return False, "❌ В ФИО не должно быть цифр! Попробуй ещё раз."
    
    for char in name:
        if not (char.isalpha() or char.isspace() or char in '-.'):
            return False, "❌ В ФИО нельзя использовать специальные символы! Попробуй ещё раз."
    
    if not any(char.isalpha() for char in name):
        return False, "❌ ФИО должно содержать хотя бы одну букву!"
    
    if '  ' in name or '--' in name or '- ' in name or ' -' in name:
        return False, "❌ Некорректное использование пробелов или дефисов!"
    
    return True, None

def get_role_keyboard():
    builder = InlineKeyboardBuilder()
    for role_key, role_name in ROLES.items():
        builder.button(text=role_name, callback_data=f"role_{role_key}")
    builder.adjust(2)
    return builder.as_markup()

def get_timezone_keyboard():
    builder = InlineKeyboardBuilder()
    for tz_key, tz_name in TIMEZONES.items():
        builder.button(text=tz_name, callback_data=f"tz_{tz_key}")
    builder.adjust(2)
    return builder.as_markup()

# DONE
@router.message(CommandStart())
async def cmd_start_handler(message: Message, state: FSMContext) -> None:
    user_id = int(message.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    
    if user is not None:
        await message.answer(
            f"<b>Приветик, {html.quote(user.full_name)}!</b>\n\n"
            f"✅ Ты уже зарегистрирован(а)!",
            parse_mode="HTML"
        )
    else:
        await state.set_state(RegistrationStates.waiting_for_name)
        await message.answer(
            "👋 <b>Приветик приветик!</b>\n\n"
            "Я — бот-ассистент хакатона 🤖\n\n"
            "Чем могу помочь:\n"
            "• 📅 Расписание и даты\n"
            "• 🎯 Темы и направления \n"
            "• 👥 Формирование команд\n"
            "• 🏆 Призы и критерии\n"
            "• 💡 Советы и помощь\n\n"
            "📝 Для начала работы нужно пройти регистрацию.\n"
            "Пожалуйста, введи свое <b>ФИО</b>:",
            parse_mode="HTML"
        )

# DONE
@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()

    is_valid, error_message = validate_name(name)
    if not is_valid:
        await message.answer(error_message)
        return
    
    await state.update_data(full_name=name)
    
    await state.set_state(RegistrationStates.waiting_for_role)
    
    await message.answer(
        f"✅ <b>Отлично, {html.quote(name)}!</b>\n\n"
        "Теперь выбери твою роль:",
        reply_markup=get_role_keyboard(),
        parse_mode="HTML"
    )

# DONE
@router.callback_query(F.data.startswith("role_"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    role_key = callback.data.replace("role_", "")
    
    if role_key not in ROLES:
        await callback.answer("❌ Ой, что ты такое навыбирал... давай-ка ещё раз", show_alert=True)
        return
    
    await state.update_data(role=role_key)
    
    await state.set_state(RegistrationStates.waiting_for_timezone)
    
    await callback.message.edit_text(
        f"✅ Роль <b>{ROLES[role_key]}</b> выбрана!\n\n"
        "Теперь выбери часовой пояс:",
        reply_markup=get_timezone_keyboard(),
        parse_mode="HTML"
    )
    
    await callback.answer()

# DONE
@router.callback_query(F.data.startswith("tz_"))
async def process_timezone(callback: CallbackQuery, state: FSMContext):
    tz_key = callback.data.replace("tz_", "")
    
    if tz_key not in TIMEZONES:
        await callback.answer("❌ Ой, что-то ты такое навыбирал... давай-ка ещё раз", show_alert=True)
        return
    
    user_data = await state.get_data()
    
    if "full_name" not in user_data or "role" not in user_data:
        await callback.message.edit_text(
            "❌ <b>Очень жаль. Регистрация не удалась.</b>\n\n"
            "Нужно пройти её заново /start",
            parse_mode="HTML"
        )
        await state.clear()
        await callback.answer()
        return
    
    user_id = int(callback.from_user.id)
    user = await UserService().create_user(user_id, callback.from_user.username, user_data["full_name"], user_data["role"], tz_key)
    
    await state.clear()
    
    await callback.message.edit_text(
        f"🎉 <b>Регистрация завершена!</b>\n\n"
        f"<b>Ваши данные:</b>\n"
        f"<b>ФИО:</b> {html.quote(user.full_name)}\n"
        f"<b>Роль:</b> {ROLES[user.role]}\n"
        f"<b>Часовой пояс:</b> {user.timezone}\n\n"
        f"Используй /menu для открытия главного меню",
        parse_mode="HTML"
    )
    
    await callback.answer()

# DONE
@router.message(F.text == "/users")
async def show_all_users(message: Message):
    user_id = int(message.from_user.id)
    user_serv = UserService()
    user = await user_serv.get_by_tg_id(user_id)
    
    if not user:
        await message.answer(
            "❌ <b>Сначала зарегистрируйся!</b>\n\n"
            "Жми /start",
            parse_mode="HTML"
        )
        return
    
    if user.role != "organizer":
        await message.answer(
            "🚫 <b>Доступ запрещен!</b>\n\n"
            "Эта команда только для организаторов.",
            parse_mode="HTML"
        )
        return
    
    participants = await user_serv.get_all_participants()
    if len(participants) == 0:
        await message.answer(
            "📭 <b>Нет зарегистрированных пользователей</b>",
            parse_mode="HTML"
        )
        return
    
    text = "👥 <b>Зарегистрированные пользователи:</b>\n\n"
    user_cnt = 0
    
    for part in participants:
        user_cnt += 1
        username = f" @{part.username}" if part.username else ""
        text += f"{user_cnt}. {part.full_name}{username}\n"
        text += f"Роль: {ROLES.get(str(part.role.value), 'Неизвестно')}\n"
        text += f"Часовой пояс: {TIMEZONES.get(part.timezone, 'Неизвестно')}\n"
        text += f"ID: {part.id}\n\n"
    
    text += f"📊 <b>Всего пользователей:</b> {user_cnt}"
    
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

@router.message(F.text == "/reset")
async def reset_registration(message: Message, state: FSMContext):
    user_id = int(message.from_user.id)
    user_serv = UserService()
    user = await user_serv.get_by_tg_id(user_id)
    
    if user:
        await user_serv.delete_user(user_id)
        await message.answer(
            "🔄 <b>Регистрация сброшена!</b>\n\n"
            "Используй /start для новой регистрации.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🤷 <b>Ты и так не зарегистрирован!</b>\n\n"
            "Используй /start 🚀",
            parse_mode="HTML"
        )
    
    await state.clear()

# DONE
@router.message(F.text == "/help")
async def show_help(message: Message):
    help_text = (
        "📚 <b>Доступные команды:</b>\n\n"
        "/start - Начать регистрацию\n"
        "/menu - Главное меню\n"
        "/reset - Сбросить регистрацию\n"
        "/help - Показать справку\n\n"
    )
    
    user_id = int(message.from_user.id)
    user = await UserService().get_by_tg_id(user_id)
    if user and user.role == "organizer":
        help_text += "/users - Показать всех пользователей\n"
    
    await message.answer(help_text, parse_mode="HTML")