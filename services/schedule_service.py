# services/schedule_service.py
"""
Сервисный слой для работы с расписанием.
Бизнес-логика для событий и уведомлений.
Соответствует оригинальному ScheduleService из кода.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from aiogram import Bot
from aiogram.types import Message

from repositories.schedule_repository import ScheduleRepository
from repositories.user_repository import UserRepository
from models.schedule import Event, EventLog, EventNotification, EventChangeType
from models.user import User, UserRole

TIMEZONE_OFFSETS = {
    "UTC+3": 3, "UTC+4": 4, "UTC+5": 5, "UTC+6": 6,
    "UTC+7": 7, "UTC+8": 8, "UTC+9": 9, "UTC+10": 10,
}


class ScheduleService:
    """Сервис для работы с расписанием."""

    def __init__(
        self, 
        schedule_repository: ScheduleRepository | None = None,
        user_repository: UserRepository | None = None
    ):
        if not schedule_repository:
            self.schedule_repo = ScheduleRepository()
        else:
            self.schedule_repo = schedule_repository
        
        if not user_repository:
            self.user_repo = UserRepository()
        else:
            self.user_repo = user_repository

    # ==================== ОСНОВНЫЕ МЕТОДЫ (как в исходном коде) ====================

    async def add_event(
        self,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        visibility: List[str],
        location: str = "",
        created_by: str = "",
        creator_timezone: str = "UTC+3"
    ) -> Dict[str, Any]:
        """Добавляет новое событие."""
        # Получаем ID создателя если передан telegram_id
        user_id = None
        if created_by:
            user = await self.user_repo.get_by_telegram_id(int(created_by))
            user_id = user.id if user else None
        
        # Создаем объект события
        event = Event(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            visibility=visibility,
            created_by=user_id,
            creator_timezone=creator_timezone
        )
        
        # Сохраняем в БД
        saved_event = await self.schedule_repo.create_event(event)
        
        return saved_event.to_dict()

    async def get_events_for_role(
        self,
        role: str,
        user_timezone: str = "UTC+3",
        include_all: bool = True
    ) -> List[Dict[str, Any]]:
        """Возвращает события для указанной роли."""
        events = await self.schedule_repo.get_events_for_role(role, user_timezone, include_all)
        
        result = []
        for event in events:
            event_dict = event.to_dict(user_timezone)
            # Добавляем конвертированное время
            start_local, end_local = self._convert_time_for_user(
                event.start_time,
                event.creator_timezone,
                user_timezone
            )
            event_dict["start_time_local"] = start_local
            event_dict["end_time_local"] = end_local
            result.append(event_dict)
        
        return result

    def _convert_time_for_user(
        self, 
        event_time: datetime, 
        event_timezone: str, 
        user_timezone: str
    ) -> datetime:
        """Конвертирует время в часовой пояс пользователя."""
        event_offset = TIMEZONE_OFFSETS.get(event_timezone, 3)
        user_offset = TIMEZONE_OFFSETS.get(user_timezone, 3)
        
        time_diff = user_offset - event_offset
        return event_time + timedelta(hours=time_diff)

    async def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Находит событие по ID."""
        event = await self.schedule_repo.get_event_by_id(event_id)
        if event:
            return event.to_dict()
        return None
    
    async def events_by_days_to_display(
        self,
        role: str,
        user_timezone: str
    ) -> str:
        
        events = await get_events_for_role(role)
        text = ""
        events_by_day = {}
        for event in events:
            local_time = _convert_time_for_user(
                event.start_time, 
                event.creator_timezone, 
                user_timezine)
            day = local_time.strftime("%d.%m.%Y")
            if day not in events_by_day:
                events_by_day[day] = []
            events_by_day[day].append(event)
        
        for day, day_events in sorted(events_by_day.items()):
        text += f"<b>📆 {day}</b>\n"
        for event in day_events:
            start_time_local  = _convert_time_for_user(
                event.start_time, 
                event.creator_timezone, 
                user_timezine)
            
            end_time_local = _convert_time_for_user(
                event.start_time, 
                event.creator_timezone, 
                user_timezine)
            
            start_str = start_time_local.strftime("%H:%M")
            end_str = end_time_local.strftime("%H:%M")
            text += f"\n<b>• {start_str} - {end_str}</b>\n<i>{event['title']}</i>\n"
            if event.get("location"):
                text += f"📍 {event['location']}\n"
        
        return text

    async def update_event(self, event_id: int, **kwargs) -> bool:
        """Обновляет данные события."""
        success = await self.schedule_repo.update_event(event_id, **kwargs)
        
        if success:
            # Логируем изменения
            event = await self.schedule_repo.get_event_by_id(event_id)
            if event:
                await self.schedule_repo.create_event_log(
                    EventLog(
                        event_id=event_id,
                        changed_by=None,  # Можно добавить user_id если есть
                        change_type=EventChangeType.UPDATED,
                        changes=kwargs
                    )
                )
        
        return success

    async def delete_event(self, event_id: int) -> bool:
        """Удаляет событие."""
        event = await self.schedule_repo.get_event_by_id(event_id)
        if not event:
            return False
        
        success = await self.schedule_repo.delete_event_hard(event_id)
        
        if success:
            # Логируем удаление
            await self.schedule_repo.create_event_log(
                EventLog(
                    event_id=event_id,
                    changed_by=None,  # Можно добавить user_id если есть
                    change_type=EventChangeType.DELETED,
                    changes=event.to_dict()
                )
            )
        
        return success

    async def get_all_events(self) -> List[Dict[str, Any]]:
        """Возвращает все события."""
        events = await self.schedule_repo.get_all_events()
        return [event.to_dict() for event in events]

    def format_event_for_display(
        self, 
        event: Dict[str, Any], 
        user_timezone: str = "UTC+3"
    ) -> str:
        """Форматирует событие для отображения."""
        # Конвертируем время
        start_local = self._convert_time_for_user(
            event["start_time"],
            event.get("creator_timezone", "UTC+3"),
            user_timezone
        )
        end_local = self._convert_time_for_user(
            event["end_time"],
            event.get("creator_timezone", "UTC+3"),
            user_timezone
        )
        
        start = start_local.strftime("%d.%m %H:%M")
        end = end_local.strftime("%H:%M")
        
        text = (
            f"📅 <b>{event['title']}</b>\n"
            f"🕒 {start} - {end}\n"
        )
        
        if event.get("location"):
            text += f"📍 {event['location']}\n"
        
        if event.get("description"):
            text += f"\n{event['description']}\n"
        
        visibility = event.get("visibility", [])
        if "all" in visibility:
            text += "\n<i>Для всех участников</i>"
        else:
            roles_display = []
            role_emojis = {
                "participant": "👤",
                "organizer": "🎪",
                "mentor": "🧠",
                "volunteer": "🤝"
            }
            
            for role in visibility:
                if role in role_emojis:
                    roles_display.append(role_emojis[role])
            
            if roles_display:
                text += f"\n<i>Для: {' '.join(roles_display)}</i>"
        
        return text

    # ==================== МЕТОДЫ С УВЕДОМЛЕНИЯМИ ====================

    async def add_event_with_notification(
        self,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        visibility: List[str],
        location: str = "",
        created_by: str = "",
        creator_timezone: str = "UTC+3",
        bot: Optional[Bot] = None,
        temp_users_storage: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Добавляет событие с отправкой уведомлений."""
        # Создаем событие
        event_dict = await self.add_event(
            title, description, start_time, end_time,
            visibility, location, created_by, creator_timezone
        )
        
        event = await self.schedule_repo.get_event_by_id(event_dict["id"])
        
        # Отправляем уведомления если есть бот
        if bot and event:
            await self._notify_new_event(bot, event, temp_users_storage)
        
        return event_dict

    async def update_event_with_notification(
        self,
        event_id: int,
        bot: Optional[Bot] = None,
        temp_users_storage: Optional[Dict] = None,
        **kwargs
    ) -> bool:
        """Обновляет событие с отправкой уведомлений."""
        old_event = await self.schedule_repo.get_event_by_id(event_id)
        if not old_event:
            return False
        
        changes = {}
        for key, value in kwargs.items():
            if getattr(old_event, key, None) != value:
                if key != "visibility":
                    changes[key] = value
        
        success = await self.update_event(event_id, **kwargs)
        
        if success and changes and bot and old_event:
            new_event = await self.schedule_repo.get_event_by_id(event_id)
            await self._notify_event_updated(bot, new_event, changes, temp_users_storage)
        
        return success

    async def delete_event_with_notification(
        self,
        event_id: int,
        bot: Optional[Bot] = None,
        temp_users_storage: Optional[Dict] = None
    ) -> bool:
        """Удаляет событие с отправкой уведомлений."""
        event = await self.schedule_repo.get_event_by_id(event_id)
        if not event:
            return False
        
        # Сохраняем данные для уведомления
        event_data = event.to_dict()
        
        success = await self.delete_event(event_id)
        
        if success and bot and temp_users_storage:
            await self._notify_event_cancelled(bot, event_data, temp_users_storage)
        
        return success

    # ==================== ПРИВАТНЫЕ МЕТОДЫ ДЛЯ УВЕДОМЛЕНИЙ ====================

    async def _notify_new_event(
        self, 
        bot: Bot, 
        event: Event,
        temp_users_storage: Dict
    ):
        """Отправляет уведомления о новом событии."""
        # Получаем пользователей, которым нужно отправить уведомление
        if "all" in event.visibility:
            # Временно: используем temp_users_storage
            for user_id, user_data in temp_users_storage.items():
                try:
                    if event.is_visible_for_role(user_data["role"]):
                        await bot.send_message(
                            chat_id=int(user_id),
                            text=f"📅 <b>Новое событие!</b>\n\n{self.format_event_for_display(event.to_dict(), user_data.get('timezone', 'UTC+3'))}",
                            parse_mode="HTML"
                        )
                except Exception as e:
                    print(f"Error sending notification to {user_id}: {e}")

    async def _notify_event_updated(
        self,
        bot: Bot,
        event: Event,
        changes: Dict[str, Any],
        temp_users_storage: Dict
    ):
        """Отправляет уведомления об изменении события."""
        # Определяем, что изменилось
        change_messages = []
        if "title" in changes:
            change_messages.append(f"Название: {changes['title']}")
        if "start_time" in changes:
            change_messages.append(f"Время начала")
        if "location" in changes:
            change_messages.append(f"Место проведения")
        if "description" in changes:
            change_messages.append(f"Описание")
        
        if not change_messages:
            return
        
        # Отправляем уведомления
        for user_id, user_data in temp_users_storage.items():
            try:
                if event.is_visible_for_role(user_data["role"]):
                    await bot.send_message(
                        chat_id=int(user_id),
                        text=f"📅 <b>Событие обновлено!</b>\n\n"
                             f"Изменения: {', '.join(change_messages)}\n\n"
                             f"{self.format_event_for_display(event.to_dict(), user_data.get('timezone', 'UTC+3'))}",
                        parse_mode="HTML"
                    )
            except Exception as e:
                print(f"Error sending update notification to {user_id}: {e}")

    async def _notify_event_cancelled(
        self,
        bot: Bot,
        event_data: Dict[str, Any],
        temp_users_storage: Dict
    ):
        """Отправляет уведомления об отмене события."""
        for user_id, user_data in temp_users_storage.items():
            try:
                # Проверяем видимость события для пользователя
                visibility = event_data.get("visibility", [])
                user_role = user_data["role"]
                
                if "all" in visibility or user_role in visibility:
                    await bot.send_message(
                        chat_id=int(user_id),
                        text=f"❌ <b>Событие отменено!</b>\n\n"
                             f"<b>{event_data['title']}</b>\n"
                             f"🕒 {event_data['start_time'].strftime('%d.%m %H:%M')}",
                        parse_mode="HTML"
                    )
            except Exception as e:
                print(f"Error sending cancellation notification to {user_id}: {e}")

    # ==================== ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ====================

    async def get_upcoming_events_for_role(
        self, 
        role: str, 
        hours_ahead: int = 24,
        user_timezone: str = "UTC+3"
    ) -> List[Dict[str, Any]]:
        """Возвращает ближайшие события для роли."""
        events = await self.schedule_repo.get_upcoming_events(hours_ahead, role)
        
        result = []
        for event in events:
            event_dict = event.to_dict(user_timezone)
            start_local, end_local = self._convert_time_for_user(
                event.start_time,
                event.creator_timezone,
                user_timezone
            )
            event_dict["start_time_local"] = start_local
            event_dict["end_time_local"] = end_local
            result.append(event_dict)
        
        return result

    async def send_event_reminders(self, bot: Bot, temp_users_storage: Dict):
        """Отправляет напоминания о ближайших событиях."""
        now = datetime.utcnow()
        events = await self.schedule_repo.get_upcoming_events(1)  # События в ближайший час
        
        for event in events:
            # Проверяем, что событие начнется в ближайшие 15-60 минут
            time_until = (event.start_time - now).total_seconds() / 60
            if 15 <= time_until <= 60:
                # Отправляем напоминания
                for user_id, user_data in temp_users_storage.items():
                    if event.is_visible_for_role(user_data["role"]):
                        try:
                            await bot.send_message(
                                chat_id=int(user_id),
                                text=f"🔔 <b>Напоминание о событии!</b>\n\n"
                                     f"Событие <b>{event.title}</b> начнется через {int(time_until)} минут\n"
                                     f"📍 {event.location if event.location else 'Место не указано'}",
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            print(f"Error sending reminder to {user_id}: {e}")


# Создаем глобальный экземпляр сервиса
schedule_service = ScheduleService()