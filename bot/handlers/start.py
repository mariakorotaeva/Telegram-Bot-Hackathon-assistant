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
            f"<b>Приветик, {html.quote(user_data['full_name'])}!</b>\n\n"
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

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name) < 3:
        await message.answer("❌ Что-то не похоже на ФИО, попробуй ещё раз!")
        return

    if any(char.isdigit() for char in name):
        await message.answer("❌ В ФИО не должно быть цифр! Попробуй ещё раз.")
        return
    
    for char in name:
        if not (char.isalpha() or char.isspace() or char == '-'):
            await message.answer("❌ В ФИО нельзя использовать специальные символы! Попробуй ещё раз.")
            return
    
    await state.update_data(full_name=name)
    
    await state.set_state(RegistrationStates.waiting_for_role)
    
    await message.answer(
        f"✅ <b>Отлично, {html.quote(name)}!</b>\n\n"
        "Теперь выбери твою роль:",
        reply_markup=get_role_keyboard(),
        parse_mode="HTML"
    )

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
        f"🎉 <b>Регистрация завершена!</b>\n\n"
        f"<b>Ваши данные:</b>\n"
        f"<b>ФИО:</b> {html.quote(user_data['full_name'])}\n"
        f"<b>Роль:</b> {ROLES[user_data['role']]}\n"
        f"<b>Часовой пояс:</b> {TIMEZONES[tz_key]}\n\n"
        f"Используй /menu для открытия главного меню",
        parse_mode="HTML"
    )
    
    await callback.answer()

@router.message(F.text == "/profile")
async def show_profile(message: Message):
    user_id = str(message.from_user.id)
    
    if user_id in temp_users_storage:
        user_data = temp_users_storage[user_id]
        
        await message.answer(
            f"👤 <b>Ваш профиль:</b>\n\n"
            f"<b>ФИО:</b> {html.quote(user_data['full_name'])}\n"
            f"<b>Роль:</b> {ROLES.get(user_data['role'])}\n"
            f"<b>Часовой пояс:</b> {TIMEZONES.get(user_data['timezone'])}\n"
            f"<b>Telegram ID:</b> {user_id}",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>А кто это тут не зарегистрирован??</b>\n\n"
            "Ну-ка жми /start 🚀",
            parse_mode="HTML"
        )

@router.message(F.text == "/users")
async def show_all_users(message: Message):
    user_id = str(message.from_user.id)
    
    if user_id not in temp_users_storage:
        await message.answer(
            "❌ <b>Сначала зарегистрируйся!</b>\n\n"
            "Жми /start",
            parse_mode="HTML"
        )
        return
    
    if temp_users_storage[user_id]["role"] != "organizer":
        await message.answer(
            "🚫 <b>Доступ запрещен!</b>\n\n"
            "Эта команда только для организаторов.",
            parse_mode="HTML"
        )
        return
    
    if not temp_users_storage:
        await message.answer(
            "📭 <b>Нет зарегистрированных пользователей</b>",
            parse_mode="HTML"
        )
        return
    
    text = "👥 <b>Зарегистрированные пользователи:</b>\n\n"
    user_cnt = 0
    
    for id, data in temp_users_storage.items():
        user_cnt += 1
        username = f" @{data.get('username', '')}" if data.get('username') else ""
        text += f"{user_cnt}. {data['full_name']}{username}\n"
        text += f"Роль: {ROLES.get(data['role'], 'Неизвестно')}\n"
        text += f"Часовой пояс: {TIMEZONES.get(data['timezone'], 'Неизвестно')}\n"
        text += f"ID: {id}\n\n"
    
    text += f"📊 <b>Всего пользователей:</b> {user_cnt}"
    
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

@router.message(F.text == "/reset")
async def reset_registration(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    
    if user_id in temp_users_storage:
        del temp_users_storage[user_id]
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

@router.message(F.text == "/help")
async def show_help(message: Message):
    help_text = (
        "📚 <b>Доступные команды:</b>\n\n"
        "/start - Начать регистрацию\n"
        "/profile - Показать профиль\n"
        "/menu - Главное меню\n"
        "/reset - Сбросить регистрацию\n"
        "/help - Показать справку\n\n"
    )
    
    user_id = str(message.from_user.id)
    if user_id in temp_users_storage and temp_users_storage[user_id]["role"] == "organizer":
        help_text += "/users - Показать всех пользователей\n"
    
    await message.answer(help_text, parse_mode="HTML")