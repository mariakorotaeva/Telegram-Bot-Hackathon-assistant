import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from enum import Enum
from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..services.schedule_service import schedule_service, TIMEZONE_OFFSETS

router = Router()

notifications_storage = {
    "settings": {},
    "sent_reminders": {}
}

class NotificationType(Enum):
    SCHEDULE_REMINDER = "schedule_reminder"
    NEW_EVENT = "new_event"
    EVENT_UPDATED = "event_updated"
    EVENT_CANCELLED = "event_cancelled"

def get_default_notification_settings(role: str = "participant"):
    default_settings = {
        "enabled": True,
        "reminder_minutes": [5, 15, 60],
        "new_event_enabled": True,
        "event_updated_enabled": True,
        "event_cancelled_enabled": True
    }
    
    if role == "organizer":
        default_settings.update({
            "new_event_enabled": False,
            "event_updated_enabled": False,
            "event_cancelled_enabled": False
        })
    
    return default_settings

class NotificationStates(StatesGroup):
    editing_reminders = State()
    editing_types = State()

async def send_notification(
    bot: Bot,
    user_id: str,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.SCHEDULE_REMINDER,
    user_role: str = "participant"
):
    try:
        settings = notifications_storage["settings"].get(user_id, get_default_notification_settings(user_role))
        
        if not settings.get("enabled", True):
            return False
        
        if notification_type == NotificationType.NEW_EVENT and not settings.get("new_event_enabled", True):
            return False
        elif notification_type == NotificationType.EVENT_UPDATED and not settings.get("event_updated_enabled", True):
            return False
        elif notification_type == NotificationType.EVENT_CANCELLED and not settings.get("event_cancelled_enabled", True):
            return False
        
        await bot.send_message(
            user_id,
            f"<b>{title}</b>\n\n{message}",
            parse_mode="HTML"
        )
        return True
    except Exception as e:
        print(f"Error sending notification to {user_id}: {e}")
        return False

async def check_and_send_reminders(bot: Bot, temp_users_storage: Dict):
    current_time_utc = datetime.utcnow()
    
    for user_id, user_data in temp_users_storage.items():
        settings = notifications_storage["settings"].get(user_id, get_default_notification_settings())
        
        if not settings.get("enabled", True):
            continue
            
        role = user_data.get("role", "participant")
        user_timezone = user_data.get("timezone", "UTC+3")
        
        events = schedule_service.get_events_for_role(role, user_timezone)
        
        for event in events:
            creator_tz = event.get('creator_timezone', 'UTC+3')
            creator_offset = TIMEZONE_OFFSETS.get(creator_tz, 3)
            
            event_time_utc = event['start_time'] - timedelta(hours=creator_offset)
            
            time_diff_seconds = (event_time_utc - current_time_utc).total_seconds()
            
            if time_diff_seconds <= 0:
                continue
            
            reminder_minutes = settings.get("reminder_minutes", get_default_notification_settings()["reminder_minutes"])
            
            for reminder_mins in reminder_minutes:
                reminder_seconds = reminder_mins * 60
                
                seconds_from_reminder = time_diff_seconds - reminder_seconds
                
                if -30 <= seconds_from_reminder <= 0:
                    sent_key = f"{event['id']}:{reminder_mins}"
                    user_sent = notifications_storage["sent_reminders"].setdefault(user_id, set())
                    
                    if sent_key not in user_sent:
                        start_str = event['start_time'].strftime("%d.%m.%Y %H:%M")
                        message = f"<b>{event['title']}</b>\n🕒 Начало: {start_str}\n"
                        
                        if event.get("location"):
                            message += f"📍 Место: {event['location']}\n"
                        
                        if event.get("description"):
                            desc = event['description'][:200]
                            if len(event['description']) > 200:
                                desc += "..."
                            message += f"\n{desc}\n"
                        
                        try:
                            await bot.send_message(
                                user_id,
                                f"🔔 <b>Напоминание: через {reminder_mins} минут</b>\n\n{message}",
                                parse_mode="HTML"
                            )
                            user_sent.add(sent_key)
                        except Exception:
                            pass

async def schedule_reminder_checker(bot: Bot, temp_users_storage: Dict):
    while True:
        try:
            await check_and_send_reminders(bot, temp_users_storage)
        except Exception as e:
            print(f"Error in reminder checker: {e}")
        
        await asyncio.sleep(30)

def get_notification_settings_keyboard(user_id: str):
    settings = notifications_storage["settings"].get(user_id, get_default_notification_settings())
    
    builder = InlineKeyboardBuilder()
    
    enabled_status = "🔕 Выключить" if settings["enabled"] else "🔔 Включить"

    builder.button(text=enabled_status, callback_data="toggle_notifications")
    builder.button(text="⏰ Время напоминаний", callback_data="edit_reminders")
    builder.button(text="📋 Типы уведомлений", callback_data="edit_types")
    builder.button(text="🔙 Назад в меню", callback_data="back_to_menu")
    
    builder.adjust(2, 2)
    return builder.as_markup()

def get_reminder_time_keyboard(selected_minutes: List[int]):
    times = [2, 5, 15, 30, 60, 90, 120]
    
    builder = InlineKeyboardBuilder()
    
    for minutes in times:
        hours = minutes // 60
        minutes_remain = minutes % 60
        
        if hours > 0:
            text = f"{hours}ч"
            if minutes_remain > 0:
                text += f" {minutes_remain}м"
        else:
            text = f"{minutes}м"
        
        if minutes in selected_minutes:
            text = f"✅ {text}"
        else:
            text = f"◻️ {text}"
        
        builder.button(text=text, callback_data=f"reminder_{minutes}")
    
    builder.button(text="✅ Готово", callback_data="reminders_done")
    builder.button(text="❌ Сбросить", callback_data="reminders_reset")
    builder.button(text="🔙 Назад", callback_data="notifications_back")
    
    builder.adjust(3, 3, 2)
    return builder.as_markup()

def get_notification_types_keyboard(settings: Dict):
    builder = InlineKeyboardBuilder()
    
    new_event_text = "✅ Новые события" if settings.get("new_event_enabled", True) else "◻️ Новые события"
    builder.button(text=new_event_text, callback_data="toggle_new_events")
    
    updated_text = "✅ Изменения" if settings.get("event_updated_enabled", True) else "◻️ Изменения"
    builder.button(text=updated_text, callback_data="toggle_event_updates")
    
    cancelled_text = "✅ Отмена" if settings.get("event_cancelled_enabled", True) else "◻️ Отмена"
    builder.button(text=cancelled_text, callback_data="toggle_event_cancelled")
    
    builder.button(text="✅ Готово", callback_data="types_done")
    builder.button(text="🔙 Назад", callback_data="notifications_back")
    
    builder.adjust(1, 1, 1, 2)
    return builder.as_markup()

@router.callback_query(F.data == "menu_notifications")
async def notifications_menu(callback: CallbackQuery):
    user_id = str(callback.from_user.id)

    from .menu import temp_users_storage as users_storage
    user_data = users_storage.get(user_id, {})
    role = user_data.get("role", "participant")
    
    settings = notifications_storage["settings"].setdefault(user_id, get_default_notification_settings(role))
    
    status = "✅ Включены" if settings["enabled"] else "❌ Выключены"
    
    minutes = settings.get("reminder_minutes", get_default_notification_settings()["reminder_minutes"])
    times_display = []
    for m in sorted(minutes):
        if m < 60:
            times_display.append(f"{m}м")
        else:
            hours = m // 60
            mins = m % 60
            if mins > 0:
                times_display.append(f"{hours}ч {mins}м")
            else:
                times_display.append(f"{hours}ч")
    
    types_active = []
    if settings.get("new_event_enabled", True):
        types_active.append("новые")
    if settings.get("event_updated_enabled", True):
        types_active.append("изменения")
    if settings.get("event_cancelled_enabled", True):
        types_active.append("отмена")
    
    await callback.message.edit_text(
        f"🔔 <b>Управление уведомлениями</b>\n\n"
        f"Статус: {status}\n\n"  # Убрал: {mute_info}
        f"⏰ Напоминания за: {', '.join(times_display)}\n"
        f"📋 Активные уведомления: {', '.join(types_active) if types_active else 'нет'}\n\n"
        f"Здесь вы можете настроить получение уведомлений о событиях хакатона.",
        reply_markup=get_notification_settings_keyboard(user_id),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery):
    user_id = str(callback.from_user.id)

    from .menu import temp_users_storage as users_storage
    user_data = users_storage.get(user_id, {})
    role = user_data.get("role", "participant")

    settings = notifications_storage["settings"].setdefault(user_id, get_default_notification_settings(role))
    
    settings["enabled"] = not settings["enabled"]
    
    await callback.message.edit_text(
        f"✅ Уведомления {'включены' if settings['enabled'] else 'выключены'}!",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(1)
    await notifications_menu(callback)

@router.callback_query(F.data == "edit_reminders")
async def edit_reminders(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    settings = notifications_storage["settings"].setdefault(user_id, get_default_notification_settings())
    
    await state.set_state(NotificationStates.editing_reminders)
    await state.update_data(selected_minutes=settings.get("reminder_minutes", get_default_notification_settings()["reminder_minutes"]).copy())
    
    await callback.message.edit_text(
        "⏰ <b>Настройка времени напоминаний</b>\n\n"
        "Выберите за сколько времени до события приходить уведомления:\n"
        "(Можно выбрать несколько вариантов)",
        reply_markup=get_reminder_time_keyboard(settings.get("reminder_minutes", [15, 60])),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("reminder_"), NotificationStates.editing_reminders)
async def toggle_reminder_time(callback: CallbackQuery, state: FSMContext):
    minutes = int(callback.data.replace("reminder_", ""))
    
    data = await state.get_data()
    selected_minutes = data.get("selected_minutes", [])
    
    if minutes in selected_minutes:
        selected_minutes.remove(minutes)
    else:
        selected_minutes.append(minutes)
    
    await state.update_data(selected_minutes=selected_minutes)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_reminder_time_keyboard(selected_minutes)
    )
    await callback.answer()

@router.callback_query(F.data == "reminders_done", NotificationStates.editing_reminders)
async def save_reminders(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    data = await state.get_data()
    selected_minutes = data.get("selected_minutes", [15, 60])
    
    selected_minutes.sort()
    notifications_storage["settings"].setdefault(user_id, get_default_notification_settings())
    notifications_storage["settings"][user_id]["reminder_minutes"] = selected_minutes
    
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ Время напоминаний сохранено: {', '.join(str(m) for m in selected_minutes)} минут",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(1)
    await notifications_menu(callback)

@router.callback_query(F.data == "reminders_reset", NotificationStates.editing_reminders)
async def reset_reminders(callback: CallbackQuery, state: FSMContext):
    default_settings = get_default_notification_settings()
    
    await state.update_data(selected_minutes=default_settings["reminder_minutes"].copy())
    
    await callback.message.edit_reply_markup(
        reply_markup=get_reminder_time_keyboard(default_settings["reminder_minutes"])
    )
    await callback.answer("Настройки сброшены!")

@router.callback_query(F.data == "edit_types")
async def edit_notification_types(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    settings = notifications_storage["settings"].setdefault(user_id, get_default_notification_settings())
    
    await state.set_state(NotificationStates.editing_types)
    
    await callback.message.edit_text(
        "📋 <b>Настройка типов уведомлений</b>\n\n"
        "Выберите какие уведомления вы хотите получать:\n\n"
        "• <b>Новые события</b> - при добавлении новых событий в расписание\n"
        "• <b>Изменения</b> - при изменении времени или места событий\n"
        "• <b>Отмена</b> - при отмене событий",
        reply_markup=get_notification_types_keyboard(settings),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.in_(["toggle_new_events", "toggle_event_updates", "toggle_event_cancelled"]))
async def toggle_notification_type(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    settings = notifications_storage["settings"].setdefault(user_id, get_default_notification_settings())
    
    if callback.data == "toggle_new_events":
        settings["new_event_enabled"] = not settings.get("new_event_enabled", True)
    elif callback.data == "toggle_event_updates":
        settings["event_updated_enabled"] = not settings.get("event_updated_enabled", True)
    elif callback.data == "toggle_event_cancelled":
        settings["event_cancelled_enabled"] = not settings.get("event_cancelled_enabled", True)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_notification_types_keyboard(settings)
    )
    await callback.answer()

@router.callback_query(F.data == "types_done", NotificationStates.editing_types)
async def save_notification_types(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    await callback.message.edit_text(
        "✅ Настройки типов уведомлений сохранены!",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(1)
    await notifications_menu(callback)

@router.callback_query(F.data == "notifications_back")
async def back_to_notifications(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await notifications_menu(callback)

async def notify_new_event(bot: Bot, event: Dict, temp_users_storage: Dict):
    from .menu import temp_users_storage as users_storage
    
    for user_id, user_data in users_storage.items():
        role = user_data.get("role", "participant")
        
        if "all" in event["visibility"] or role in event["visibility"]:
            timezone = user_data.get("timezone", "UTC+3")
            start_local = schedule_service._convert_time_for_user(
                event["start_time"],
                event.get("creator_timezone", "UTC+3"),
                timezone
            )
            
            start_str = start_local.strftime("%d.%m.%Y %H:%M")
            
            message = (
                f"<b>{event['title']}</b>\n"
                f"🕒 Начало: {start_str}\n"
            )
            
            if event.get("location"):
                message += f"📍 Место: {event['location']}\n"
            
            if event.get("description"):
                message += f"\n{event['description'][:200]}\n"
            
            await send_notification(
                bot,
                user_id,
                "📢 Добавлено новое событие",
                message,
                NotificationType.NEW_EVENT,
                user_role=role
            )

async def notify_event_updated(bot: Bot, event: Dict, changes: Dict, temp_users_storage: Dict):
    from .menu import temp_users_storage as users_storage
    
    for user_id, user_data in users_storage.items():
        role = user_data.get("role", "participant")
        
        if "all" in event["visibility"] or role in event["visibility"]:
            changes_details = []
            
            if "title" in changes:
                changes_details.append(f"<b>Название:</b> {event['title']}")
            
            if "start_time" in changes:
                new_time = event['start_time'].strftime('%d.%m.%Y %H:%M')
                changes_details.append(f"<b>Время начала:</b> {new_time}")
            
            if "location" in changes:
                location = event.get('location')
                if location == '':
                    location = 'удалено'
                changes_details.append(f"<b>Место:</b> {location}")
            
            if "description" in changes:
                description = event.get('description', '')
                if description:
                    desc_preview = description[:100] + "..." if len(description) > 100 else description
                    changes_details.append(f"<b>Описание:</b> {desc_preview}")
                else:
                    changes_details.append("<b>Описание:</b> удалено")
            
            if "end_time" in changes and "start_time" not in changes:
                duration_minutes = int((event['end_time'] - event['start_time']).total_seconds() / 60)
                hours = duration_minutes // 60
                minutes = duration_minutes % 60
                if hours > 0:
                    duration_str = f"{hours}ч {minutes}м"
                else:
                    duration_str = f"{minutes}м"
                changes_details.append(f"<b>Продолжительность:</b> {duration_str}")
            
            message = (
                    f"<b>{event.get('title')}</b>\n\n"
                    f"Новые данные:\n" + "\n".join(changes_details)
                )
            
            await send_notification(
                bot,
                user_id,
                "✏️ Изменение в расписании",
                message,
                NotificationType.EVENT_UPDATED,
                user_role=role
            )

async def notify_event_cancelled(bot: Bot, event: Dict, temp_users_storage: Dict):
    from .menu import temp_users_storage as users_storage
    
    for user_id, user_data in users_storage.items():
        role = user_data.get("role", "participant")
        
        if "all" in event["visibility"] or role in event["visibility"]:
            message = (
                f"<b>{event['title']}</b>\n"
                f"Запланированное на {event['start_time'].strftime('%d.%m.%Y %H:%M')}\n"
            )
            
            await send_notification(
                bot,
                user_id,
                "❌ Отмена события",
                message,
                NotificationType.EVENT_CANCELLED,
                user_role=role
            )