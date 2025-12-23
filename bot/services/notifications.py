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
from services.user_service import UserService
from services.notification_service import NotificationService
from services.schedule_service import ScheduleService

notifications_storage = {
    "settings": {},
    "sent_reminders": {}
}

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

class NotificationType(Enum):
    SCHEDULE_REMINDER = "schedule_reminder"
    NEW_EVENT = "new_event"
    EVENT_UPDATED = "event_updated"
    EVENT_CANCELLED = "event_cancelled"

async def send_notification(
    bot: Bot,
    user_id: str,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.SCHEDULE_REMINDER,
    user_role: str = "participant"
):
    # try:
    # settings = notifications_storage["settings"].get(user_id, get_default_notification_settings(user_role))
    settings = await NotificationService().get_or_create_settings(user_id)

    
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
    # except Exception as e:
    #     print(f"Error sending notification to {user_id}: {e}")
    #     return False

async def check_and_send_reminders(bot: Bot):
    current_time_utc = datetime.utcnow()
    all_users = await UserService().get_all()
    
    for user in all_users:
        settings = await NotificationService().get_or_create_settings(user.telegram_id)
        
        if not settings.enabled:
            continue
            
        events = await ScheduleService().get_events_for_role(
            user.role, 
            user.timezone if user.timezone else "UTC+3"
        )
        
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
                    user_sent = notifications_storage["sent_reminders"].setdefault(user.telegram_id, set())
                    
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
                                user.telegram_id,
                                f"🔔 <b>Напоминание: через {reminder_mins} минут</b>\n\n{message}",
                                parse_mode="HTML"
                            )
                            user_sent.add(sent_key)
                        except Exception:
                            pass

async def schedule_reminder_checker(bot: Bot):
    while True:
        try:
            await check_and_send_reminders(bot)
        except Exception as e:
            print(f"Error in reminder checker: {e}")
        
        await asyncio.sleep(20)

async def notify_new_event(bot: Bot, event: Dict):
    all_users = await UserService().get_all()
    for user in all_users:
        if "all" in event["visibility"] or user.role in event["visibility"]:
            start_local = schedule_service._convert_time_for_user(
                event["start_time"],
                event.get("creator_timezone", "UTC+3"),
                user.timezone
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
                user.telegram_id,
                "📢 Добавлено новое событие",
                message,
                NotificationType.NEW_EVENT,
                user_role=role
            )

async def notify_event_updated(bot: Bot, event: Dict, changes: Dict):
    all_users = await UserService().get_all()
    for user in all_users:
        if "all" in event["visibility"] or user.role in event["visibility"]:
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
                user.telegram_id,
                "✏️ Изменение в расписании",
                message,
                NotificationType.EVENT_UPDATED,
                user_role=role
            )

async def notify_event_cancelled(bot: Bot, event: Dict):
    all_users = await UserService().get_all()
    for user in all_users:
        if "all" in event["visibility"] or user.role in event["visibility"]:
            message = (
                f"<b>{event['title']}</b>\n"
                f"Запланированное на {event['start_time'].strftime('%d.%m.%Y %H:%M')}\n"
            )
            
            await send_notification(
                bot,
                user.telegram_id,
                "❌ Отмена события",
                message,
                NotificationType.EVENT_CANCELLED,
                user_role=role
            )