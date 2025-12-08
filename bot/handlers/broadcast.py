from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from .start import temp_users_storage

router = Router()

class BroadcastStates(StatesGroup):
    waiting_for_roles = State()
    waiting_for_text = State()

def get_roles_keyboard():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👥 Всем", callback_data="broadcast_all")
    builder.button(text="👤 Участники", callback_data="broadcast_participant")
    builder.button(text="🧠 Менторы", callback_data="broadcast_mentor")
    builder.button(text="🤝 Волонтеры", callback_data="broadcast_volunteer")
    builder.button(text="🎪 Организаторы", callback_data="broadcast_organizer")
    builder.button(text="❌ Отмена", callback_data="broadcast_cancel")
    
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def back_to_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    return builder.as_markup()

async def send_broadcast(bot, role, text, sender_id):
    for user_id, user_data in temp_users_storage.items():
        if user_id == sender_id:
            continue
            
        if role != "all" and user_data.get("role") != role:
            continue
        
        try:
            await bot.send_message(
                chat_id=int(user_id),
                text=text,
                parse_mode=ParseMode.HTML
            )
        except Exception:
            continue


@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    
    if user_id not in temp_users_storage:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start")
        return
    
    user_data = temp_users_storage[user_id]
    if user_data.get("role") != "organizer":
        await callback.answer("❌ Только организаторы могут делать рассылку")
        return
    
    await state.set_state(BroadcastStates.waiting_for_roles)
    
    await callback.message.edit_text(
        "📢 <b>Создание рассылки</b>\n\n"
        "Выберите, кому отправить сообщение:",
        reply_markup=get_roles_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("broadcast_"), BroadcastStates.waiting_for_roles)
async def select_broadcast_role(callback: CallbackQuery, state: FSMContext):
    if callback.data == "broadcast_cancel":
        await state.clear()
        await callback.message.edit_text(
            "❌ Рассылка отменена",
            reply_markup=back_to_menu_keyboard()
        )
        await callback.answer()
        return
    
    role = callback.data.replace("broadcast_", "")
    
    await state.update_data(selected_role=role)
    
    await state.set_state(BroadcastStates.waiting_for_text)
    
    role_names = {
        "all": "всем пользователям",
        "participant": "участникам",
        "mentor": "менторам",
        "volunteer": "волонтерам",
        "organizer": "организаторам"
    }
    
    await callback.message.edit_text(
        f"✍️ <b>Введите текст для рассылки</b>\n\n"
        f"Получатели: <b>{role_names.get(role, role)}</b>\n\n"
        "❌ Для отмены введите /cancel",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(BroadcastStates.waiting_for_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer(
            "❌ Рассылка отменена",
            reply_markup=back_to_menu_keyboard()
        )
        return
    
    data = await state.get_data()
    selected_role = data["selected_role"]
    
    await send_broadcast(
        bot=message.bot,
        role=selected_role,
        text=message.text,
        sender_id=str(message.from_user.id)
    )
    
    role_names = {
        "all": "всем пользователи",
        "participant": "участники",
        "mentor": "менторы", 
        "volunteer": "волонтёры",
        "organizer": "организаторы"
    }
    
    await message.answer(
        f"✅ <b>Рассылка отправлена!</b>\n\n",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    
    await state.clear()

@router.message(F.text == "/cancel")
async def cancel_broadcast(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state in [BroadcastStates.waiting_for_roles, BroadcastStates.waiting_for_text]:
        await state.clear()
        await message.answer(
            "❌ Рассылка отменена",
            reply_markup=back_to_menu_keyboard()
        )