from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import re

from .menu import temp_users_storage, back_to_menu_keyboard
from bot.services.schedule_service import schedule_service, EventVisibility

router = Router()

class ScheduleStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_datetime = State()
    waiting_for_duration = State()
    waiting_for_location = State()
    waiting_for_visibility = State()
    waiting_for_edit_choice = State()
    waiting_for_edit_field = State()
    waiting_for_edit_value = State()

def get_admin_schedule_keyboard():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📅 Показать все события", callback_data="schedule_admin_view_all")
    builder.button(text="➕ Добавить событие", callback_data="schedule_admin_add")
    builder.button(text="✏️ Редактировать событие", callback_data="schedule_admin_edit")
    builder.button(text="🔙 В меню", callback_data="back_to_menu")
    
    builder.adjust(1)
    return builder.as_markup()

def get_visibility_keyboard():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👥 Для всех", callback_data="visibility_all")
    builder.button(text="👤 Участники", callback_data="visibility_participant")
    builder.button(text="🎪 Организаторы", callback_data="visibility_organizer")
    builder.button(text="🧠 Менторы", callback_data="visibility_mentor")
    builder.button(text="🤝 Волонтеры", callback_data="visibility_volunteer")
    builder.button(text="✅ Готово", callback_data="visibility_done")
    builder.button(text="❌ Отмена", callback_data="schedule_cancel")
    
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

def get_edit_event_keyboard(event_id: int):
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✏️ Название", callback_data=f"edit_title:{event_id}")
    builder.button(text="📝 Описание", callback_data=f"edit_description:{event_id}")
    builder.button(text="🕒 Время начала", callback_data=f"edit_start:{event_id}")
    builder.button(text="⏱️ Продолжительность", callback_data=f"edit_duration:{event_id}")
    builder.button(text="📍 Место", callback_data=f"edit_location:{event_id}")
    builder.button(text="👥 Видимость", callback_data=f"edit_visibility:{event_id}")
    builder.button(text="🗑️ Удалить", callback_data=f"delete_event:{event_id}")
    builder.button(text="🔙 Назад", callback_data="schedule_admin_view_all")
    
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

@router.callback_query(F.data == "menu_schedule")
async def show_schedule(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if user_id not in temp_users_storage:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    
    user_data = temp_users_storage[user_id]
    role = user_data["role"]
    user_timezone = user_data.get("timezone", "UTC+3")
    
    events = schedule_service.get_events_for_role(role, user_timezone)
    
    if not events:
        await callback.message.edit_text(
            "📅 <b>Расписание хакатона</b>\n\n"
            "На данный момент событий нет.\n",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    text = f"📅 <b>Расписание хакатона</b>\n"
    text += f"<i>Время показано в вашем часовом поясе ({user_timezone})</i>\n\n"
    
    events_by_day = {}
    for event in events:
        start_time = event.get("start_time_local", event["start_time"])
        day = start_time.strftime("%d.%m.%Y")
        if day not in events_by_day:
            events_by_day[day] = []
        events_by_day[day].append(event)
    
    for day, day_events in sorted(events_by_day.items()):
        text += f"<b>📆 {day}</b>\n"
        
        for event in day_events:
            start_time = event.get("start_time_local", event["start_time"])
            end_time = event.get("end_time_local", event["end_time"])
            
            start_str = start_time.strftime("%H:%M")
            end_str = end_time.strftime("%H:%M")
            
            text += (
                f"\n<b>• {start_str} - {end_str}</b>\n"
                f"<i>{event['title']}</i>\n"
            )
            
            if event.get("location"):
                text += f"📍 {event['location']}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_edit_schedule")
async def admin_schedule_menu(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    
    if user_id not in temp_users_storage:
        await callback.answer("❌ Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    
    user_data = temp_users_storage[user_id]
    if user_data["role"] != "organizer":
        await callback.answer("❌ Эта функция доступна только организаторам", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎪 <b>Управление расписанием</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_schedule_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "schedule_admin_view_all")
async def admin_view_all_events(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    user_data = temp_users_storage.get(user_id, {})
    user_timezone = user_data.get("timezone", "UTC+3")
    
    events = schedule_service.get_all_events()
    
    if not events:
        await callback.message.edit_text(
            "📋 <b>Все события</b>\n\n"
            "Событий пока нет.",
            reply_markup=get_admin_schedule_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    text = f"📋 <b>Все события</b>\n"
    text += f"<i>Время показано в вашем часовом поясе ({user_timezone})</i>\n\n"
    
    org_events = schedule_service.get_events_for_role("organizer", user_timezone)
    
    for event in events:
        event_with_tz = next((e for e in org_events if e["id"] == event["id"]), event)
        text += schedule_service.format_event_for_display(event_with_tz, user_timezone)
        text += f"\n{'─' * 30}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_schedule_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "schedule_admin_add")
async def start_add_event(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(ScheduleStates.waiting_for_title)
    await state.update_data(visibility=[])
    
    await callback.message.edit_text(
        "📝 <b>Добавление нового события</b>\n\n"
        "Введите название события:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ScheduleStates.waiting_for_title)
async def process_event_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(ScheduleStates.waiting_for_description)
    
    await message.answer(
        "📝 Теперь введите описание события:\n\n"
        "<i>Можно пропустить, отправив '-'</i>",
        parse_mode="HTML"
    )

@router.message(ScheduleStates.waiting_for_description)
async def process_event_description(message: Message, state: FSMContext):
    description = message.text if message.text.lower() not in "-" else ""
    await state.update_data(description=description)
    await state.set_state(ScheduleStates.waiting_for_datetime)
    
    await message.answer(
        "📅 Введите дату и время начала события:\n\n"
        "<i>Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Например: 15.12.2025 10:00</i>",
        parse_mode="HTML"
    )

@router.message(ScheduleStates.waiting_for_datetime)
async def process_event_datetime(message: Message, state: FSMContext):
    try:
        datetime_str = message.text.strip()
        start_time = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")

        now = datetime.now()
        if start_time < now:
            await message.answer(
                "❌ Нельзя создать событие в прошлом!\n"
                "Пожалуйста, введите будущую дату и время.",
                show_alert=True
            )
            return
        
        await state.update_data(start_time=start_time)
        await state.set_state(ScheduleStates.waiting_for_duration)
        
        await message.answer(
            "⏱️ Введите продолжительность события в минутах:\n\n"
            "<i>Например: 60 (для 1 часа) или 90 (для 1.5 часа)</i>",
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты и времени!\n\n"
            "Пожалуйста, используйте формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 15.12.2025 10:00",
            show_alert=True
        )

@router.message(ScheduleStates.waiting_for_duration)
async def process_event_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text.strip())
        if duration <= 0:
            raise ValueError
        
        data = await state.get_data()
        start_time = data["start_time"]
        end_time = start_time + timedelta(minutes=duration)
        
        await state.update_data(end_time=end_time, duration=duration)
        await state.set_state(ScheduleStates.waiting_for_location)
        
        await message.answer(
            "📍 Введите место проведения события:\n\n"
            "<i>Можно пропустить, отправив '-'</i>",
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат!\n"
            "Пожалуйста, введите число минут (например: 60, 90, 120)",
            show_alert=True
        )

@router.message(ScheduleStates.waiting_for_location)
async def process_event_location(message: Message, state: FSMContext):
    location = message.text if message.text.lower() not in "-" else ""
    await state.update_data(location=location)
    await state.set_state(ScheduleStates.waiting_for_visibility)
    
    await message.answer(
        "👥 Выберите, для кого видно это событие:\n\n"
        "<i>Можно выбрать несколько вариантов, затем нажмите ✅</i>",
        reply_markup=get_visibility_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("visibility_"))
async def process_visibility(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    
    if action == "cancel":
        await state.clear()
        await callback.message.edit_text(
            "❌ Добавление события отменено.",
            reply_markup=get_admin_schedule_keyboard()
        )
        await callback.answer()
        return
    
    data = await state.get_data()
    visibility = data.get("visibility", [])
    
    if action == "all":
        visibility = ["all"]
    elif action == "done":
        if not visibility:
            await callback.answer("❌ Выберите хотя бы одну группу!", show_alert=True)
            return
        
        edit_event_id = data.get("edit_event_id")
        
        if edit_event_id:
            event_id = edit_event_id
            update_success = schedule_service.update_event(event_id, visibility=visibility)
            
            if update_success:
                event = schedule_service.get_event_by_id(event_id)
                user_id = str(callback.from_user.id)
                user_data = temp_users_storage.get(user_id, {})
                user_timezone = user_data.get("timezone", "UTC+3")
                
                await callback.message.edit_text(
                    "✅ <b>Событие успешно обновлено!</b>\n\n" +
                    schedule_service.format_event_for_display(event, user_timezone),
                    reply_markup=get_edit_event_keyboard(event_id),
                    parse_mode="HTML"
                )
            else:
                await callback.message.edit_text(
                    "❌ Не удалось обновить видимость события!",
                    reply_markup=get_admin_schedule_keyboard(),
                    parse_mode="HTML"
                )
            
            await state.clear()
            await callback.answer()
            return
        else:
            user_id = str(callback.from_user.id)
            user_data = temp_users_storage.get(user_id, {})
            
            creator_timezone = user_data.get("timezone", "UTC+3")
            
            event_data = {
                "title": data["title"],
                "description": data.get("description", ""),
                "start_time": data["start_time"],
                "end_time": data["end_time"],
                "location": data.get("location", ""),
                "visibility": visibility,
                "created_by": user_id,
                "creator_timezone": creator_timezone
            }
            
            event = schedule_service.add_event(**event_data)
            
            await callback.message.edit_text(
                "✅ <b>Событие успешно добавлено!</b>\n\n" +
                schedule_service.format_event_for_display(event, creator_timezone),
                reply_markup=get_admin_schedule_keyboard(),
                parse_mode="HTML"
            )
            await state.clear()
            await callback.answer()
            return
    else:
        if action in visibility:
            visibility.remove(action)
        else:
            if "all" in visibility:
                visibility = []
            visibility.append(action)
    
    await state.update_data(visibility=visibility)
    
    role_names = {
        "all": "Все",
        "participant": "Участники",
        "organizer": "Организаторы", 
        "mentor": "Менторы",
        "volunteer": "Волонтеры"
    }
    
    selected_roles = [role_names.get(role, role) for role in visibility]
    selected = ", ".join(selected_roles) if selected_roles else "не выбрано"
    
    await callback.message.edit_text(
        f"👥 Выберите, для кого видно это событие:\n\n"
        f"<b>Выбрано:</b> {selected}\n\n"
        f"<i>Можно выбрать несколько вариантов, затем нажмите ✅</i>",
        reply_markup=get_visibility_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "schedule_cancel")
async def cancel_schedule_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.",
        reply_markup=get_admin_schedule_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "schedule_admin_edit")
async def admin_edit_event_list(callback: CallbackQuery):
    events = schedule_service.get_all_events()
    
    if not events:
        await callback.message.edit_text(
            "✏️ <b>Редактирование событий</b>\n\n"
            "Событий для редактирования нет.",
            reply_markup=get_admin_schedule_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    builder = InlineKeyboardBuilder()
    
    for event in events:
        title_short = event["title"][:30] + "..." if len(event["title"]) > 30 else event["title"]
        time_str = event["start_time"].strftime("%d.%m %H:%M")
        button_text = f"{time_str} - {title_short}"
        
        builder.button(
            text=button_text,
            callback_data=f"edit_event:{event['id']}"
        )
    
    builder.button(text="🔙 Назад", callback_data="admin_edit_schedule")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "✏️ <b>Выберите событие для редактирования:</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_event:"))
async def admin_edit_event_detail(callback: CallbackQuery):
    event_id = int(callback.data.split(":")[1])
    event = schedule_service.get_event_by_id(event_id)
    
    if not event:
        await callback.answer("❌ Событие не найдено!", show_alert=True)
        return
    
    user_id = str(callback.from_user.id)
    user_data = temp_users_storage.get(user_id, {})
    user_timezone = user_data.get("timezone", "UTC+3")
    
    org_events = schedule_service.get_events_for_role("organizer", user_timezone)
    event_with_tz = next((e for e in org_events if e["id"] == event_id), event)
    
    text = "✏️ <b>Редактирование события</b>\n\n"
    text += schedule_service.format_event_for_display(event_with_tz, user_timezone)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_edit_event_keyboard(event_id),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_"))
async def admin_edit_field(callback: CallbackQuery, state: FSMContext):
    action, event_id = callback.data.split(":")
    event_id = int(event_id)
    
    event = schedule_service.get_event_by_id(event_id)
    if not event:
        await callback.answer("❌ Событие не найдено!", show_alert=True)
        return
    
    if action == "edit_title":
        await state.set_state(ScheduleStates.waiting_for_edit_value)
        await state.update_data(edit_action="title", edit_event_id=event_id)
        
        await callback.message.edit_text(
            "✏️ Введите новое название события:",
            parse_mode="HTML"
        )
    
    elif action == "edit_description":
        await state.set_state(ScheduleStates.waiting_for_edit_value)
        await state.update_data(edit_action="description", edit_event_id=event_id)
        
        await callback.message.edit_text(
            "📝 Введите новое описание события:\n\n"
            "<i>Отправьте '-' чтобы очистить</i>",
            parse_mode="HTML"
        )
    
    elif action == "edit_location":
        await state.set_state(ScheduleStates.waiting_for_edit_value)
        await state.update_data(edit_action="location", edit_event_id=event_id)
        
        await callback.message.edit_text(
            "📍 Введите новое место проведения:\n\n"
            "<i>Отправьте '-' чтобы очистить</i>",
            parse_mode="HTML"
        )
    
    elif action == "edit_start":
        await state.set_state(ScheduleStates.waiting_for_edit_value)
        await state.update_data(edit_action="start_time", edit_event_id=event_id)
        
        await callback.message.edit_text(
            "🕒 Введите новое время начала:\n\n"
            "<i>Формат: ДД.ММ.ГГГГ ЧЧ:ММ</i>",
            parse_mode="HTML"
        )
    
    elif action == "edit_duration":
        await state.set_state(ScheduleStates.waiting_for_edit_value)
        await state.update_data(edit_action="duration", edit_event_id=event_id)
        
        await callback.message.edit_text(
            "⏱️ Введите новую продолжительность в минутах:",
            parse_mode="HTML"
        )
    
    elif action == "edit_visibility":
        await state.set_state(ScheduleStates.waiting_for_visibility)
        await state.update_data(edit_event_id=event_id, visibility=event.get("visibility", []))
        
        await callback.message.edit_text(
            "👥 Выберите новую видимость события:",
            reply_markup=get_visibility_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer()

@router.message(ScheduleStates.waiting_for_edit_value)
async def process_edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    action = data["edit_action"]
    event_id = data["edit_event_id"]
    
    event = schedule_service.get_event_by_id(event_id)
    if not event:
        await message.answer("❌ Событие не найдено!", show_alert=True)
        await state.clear()
        return
    
    if action == "title":
        update_data = {"title": message.text}
    
    elif action == "description":
        value = message.text if message.text.lower() not in "-" else ""
        update_data = {"description": value}
    
    elif action == "location":
        value = message.text if message.text.lower() not in "-" else ""
        update_data = {"location": value}
    
    elif action == "start_time":
        try:
            new_start = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")

            now = datetime.now()
            if new_start < now:
                await message.answer(
                    "❌ Нельзя перенести событие в прошлое!\n"
                    "Пожалуйста, введите будущую дату и время.",
                    show_alert=True
                )
                return

            old_duration = (event["end_time"] - event["start_time"]).seconds // 60
            new_end = new_start + timedelta(minutes=old_duration)
            update_data = {"start_time": new_start, "end_time": new_end}
        except ValueError:
            await message.answer("❌ Неверный формат даты!", show_alert=True)
            return
    
    elif action == "duration":
        try:
            duration = int(message.text.strip())
            if duration <= 0:
                raise ValueError
            new_end = event["start_time"] + timedelta(minutes=duration)
            update_data = {"end_time": new_end}
        except ValueError:
            await message.answer("❌ Неверный формат!", show_alert=True)
            return
    
    schedule_service.update_event(event_id, **update_data)
    
    await message.answer(
        "✅ Событие успешно обновлено!",
        reply_markup=get_edit_event_keyboard(event_id)
    )
    await state.clear()

@router.callback_query(F.data.startswith("delete_event:"))
async def admin_delete_event(callback: CallbackQuery):
    event_id = int(callback.data.split(":")[1])
    event = schedule_service.get_event_by_id(event_id)
    
    if not event:
        await callback.answer("❌ Событие не найдено!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"confirm_delete:{event_id}")
    builder.button(text="❌ Нет, отмена", callback_data=f"edit_event:{event_id}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        f"🗑️ <b>Вы уверены, что хотите удалить событие?</b>\n\n"
        f"<b>{event['title']}</b>\n"
        f"🕒 {event['start_time'].strftime('%d.%m %H:%M')}\n\n",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_event(callback: CallbackQuery):
    event_id = int(callback.data.split(":")[1])
    
    success = schedule_service.delete_event(event_id)
    
    if success:
        await callback.message.edit_text(
            "✅ Событие успешно удалено!",
            reply_markup=get_admin_schedule_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось удалить событие!",
            reply_markup=get_admin_schedule_keyboard()
        )
    
    await callback.answer()