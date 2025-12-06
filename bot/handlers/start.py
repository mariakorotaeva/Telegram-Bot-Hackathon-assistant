from aiogram import Router, F, html
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_role = State()
    waiting_for_timezone = State()

temp_users_storage = {} #потом надо к бд подключится

ROLES = {
    "participant": "Участник",
    "organizer": "Организатор", 
    "mentor": "Ментор",
    "volunteer": "Волонтёр"
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

@router.message(CommandStart())
async def cmd_start_handler(message: Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    
    if user_id in temp_users_storage:
        user_data = temp_users_storage[user_id]
        await message.answer(
            f"Приветик, {user_data['full_name']}!\n"
            "Ты уже зарегистрирован)"
        )
    else:
        await state.set_state(RegistrationStates.waiting_for_name)
        await message.answer(
            "Приветик приветик!\n\n"
            "Для начала работы нужно пройти регистрацию.\n"
            "Пожалуйста, введи ФИО:"
        )

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("Что-то не похоже на ФИО, попробуй ещё раз)")
        return
    
    await state.update_data(full_name=message.text.strip())
    
    await state.set_state(RegistrationStates.waiting_for_role)
    
    await message.answer(
        f"Отлично, {message.text.strip()}! \n\n"
        "Теперь выбери твою роль:",
        reply_markup=get_role_keyboard()
    )

@router.callback_query(F.data.startswith("role_"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    role_key = callback.data.replace("role_", "")
    
    if role_key not in ROLES:
        await callback.answer("Ой, что ты такое навыбирал... давай-ка ещё раз")
        return
    
    await state.update_data(role=role_key)
    
    await state.set_state(RegistrationStates.waiting_for_timezone)
    
    await callback.message.edit_text(
        f"Роль {ROLES[role_key]} выбрана!\n\n"
        "Теперь выбери часовой пояс:",
        reply_markup=get_timezone_keyboard()
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("tz_"))
async def process_timezone(callback: CallbackQuery, state: FSMContext):
    tz_key = callback.data.replace("tz_", "")
    
    if tz_key not in TIMEZONES:
        await callback.answer("Ой, что-то ты такое навыбирал... давай-ка ещё раз")
        return
    
    user_data = await state.get_data()
    
    if "full_name" not in user_data or "role" not in user_data:
        await callback.message.edit_text(
            "Очень жаль. Регистрастрация не удалась. Делай всё заново. (нажми /start) "
        )
        await state.clear()
        await callback.answer()
        return
    
    user_id = str(callback.from_user.id)
    temp_users_storage[user_id] = {
        "tg_id": user_id,
        "full_name": user_data["full_name"],
        "role": user_data["role"],
        "timezone": tz_key,
        "username": callback.from_user.username,
    }
    
    await state.clear()
    
    await callback.message.edit_text(
        f"Регистрация завершена!\n\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Роль: {ROLES[user_data['role']]}\n"
        f"Часовой пояс: {TIMEZONES[tz_key]}\n\n"
        f"Используй /menu для открытия главного меню"
    )
    
    await callback.answer()

@router.message(F.text == "/profile")
async def show_profile(message: Message):
    user_id = str(message.from_user.id)
    
    if user_id in temp_users_storage:
        user_data = temp_users_storage[user_id]
        
        await message.answer(
            f"Ваш профиль:\n\n"
            f"ФИО: {user_data['full_name']}\n"
            f"Роль: {ROLES.get(user_data['role'], 'Не указана')}\n"
            f"Часовой пояс: {TIMEZONES.get(user_data['timezone'], 'Не указан')}\n"
        )
    else:
        await message.answer("А кто это тут не зарегистрирован?? Ну-ка жми /start")

@router.message(F.text == "/users")
async def show_all_users(message: Message):
    user_id = str(message.from_user.id)
    
    if user_id not in temp_users_storage:
        await message.answer("Сначала зарегистрироваться! Жми /start")
        return
    
    if temp_users_storage[user_id]["role"] != "organizer":
        await message.answer("Это только для организаторов.")
        return
    
    if not temp_users_storage:
        await message.answer("Нет зарегистрированных пользователей")
        return
    
    text = "Зарегистрированные пользователи:\n\n"
    user_cnt = 0
    
    for id, data in temp_users_storage.items():
        user_cnt += 1
        username = f" @{data.get('username', '')}" if data.get('username') else ""
        text += f"{user_cnt}. {data['full_name']}{username}\n"
        text += f"Роль: {ROLES.get(data['role'], 'Неизвестно')}\n"
        text += f"Часовой пояс: {TIMEZONES.get(data['timezone'], 'Неизвестно')}\n"
        text += f"ID: {id}\n\n"
    
    text += f"Всего пользователей: {user_cnt}"
    
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(text)

@router.message(F.text == "/reset")
async def reset_registration(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    
    if user_id in temp_users_storage:
        del temp_users_storage[user_id]
        await message.answer("Регистрация сброшена. Используй /start для новой регистрации.")
    else:
        await message.answer("Ты и так не зарегистрирован! Используй /start")
    
    await state.clear()

@router.message(F.text == "/help")
async def show_help(message: Message):
    help_text = (
        "Доступные команды:\n\n"
        "/start - Начать регистрацию\n"
        "/profile - Показать профиль\n"
        "/menu - Главное меню\n"
        "/reset - Сбросить регистрацию\n"
        "/help - Показать справку\n\n"
    )
    
    user_id = str(message.from_user.id)
    if user_id in temp_users_storage and temp_users_storage[user_id]["role"] == "organizer":
        help_text += "/users - Показать всех пользователей\n"
    
    await message.answer(help_text)