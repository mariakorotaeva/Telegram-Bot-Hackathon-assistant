"""
Сервис для работы с уведомлениями.
"""
from typing import List, Optional
from datetime import datetime

from repositories.notification_repository import NotificationSettingsRepository
from models.notification_settings import NotificationSettings


class NotificationType:
    SCHEDULE_REMINDER = "schedule_reminder"
    NEW_EVENT = "new_event"
    EVENT_UPDATED = "event_updated"
    EVENT_CANCELLED = "event_cancelled"


class NotificationService:
    
    def __init__(self):
        self.notification_repo = NotificationSettingsRepository()
        self.sent_reminders: dict[int, set] = {}
    
    async def get_or_create_settings(self, user_id: int) -> NotificationSettings:
        """Получает или создаёт настройки уведомлений пользователя."""
        return await self.notification_repo.get_or_create_settings(user_id)
    
    async def toggle_enabled(self, user_id: int) -> NotificationSettings:
        """Переключает общую доступность уведомлений."""
        return await self.notification_repo.toggle_enabled(user_id)
    
    async def update_reminder_times(self, user_id: int, reminder_minutes: List[int]) -> NotificationSettings:
        """Обновляет время напоминаний."""
        return await self.notification_repo.update_reminder_times(user_id, reminder_minutes)
    
    async def toggle_new_events(self, user_id: int) -> NotificationSettings:
        """Переключает уведомления о новых событиях."""
        return await self.notification_repo.toggle_new_events(user_id)
    
    async def toggle_event_updates(self, user_id: int) -> NotificationSettings:
        """Переключает уведомления об изменениях событий."""
        return await self.notification_repo.toggle_event_updates(user_id)
    
    async def toggle_event_cancelled(self, user_id: int) -> NotificationSettings:
        """Переключает уведомления об отмене событий."""
        return await self.notification_repo.toggle_event_cancelled(user_id)
    
    async def should_send_notification(self, user_id: int, notification_type: str) -> bool:
        """Проверяет, нужно ли отправлять уведомление пользователю."""
        settings = await self.get_or_create_settings(user_id)
        return settings.is_enabled_for_type(notification_type)
    
    def add_sent_reminder(self, user_id: int, event_id: int, reminder_minutes: int) -> None:
        """Добавляет напоминание в список отправленных."""
        key = f"{event_id}:{reminder_minutes}"
        if user_id not in self.sent_reminders:
            self.sent_reminders[user_id] = set()
        self.sent_reminders[user_id].add(key)
    
    def is_reminder_sent(self, user_id: int, event_id: int, reminder_minutes: int) -> bool:
        """Проверяет, было ли уже отправлено напоминание."""
        key = f"{event_id}:{reminder_minutes}"
        return user_id in self.sent_reminders and key in self.sent_reminders[user_id]
    
    async def get_users_for_notification(self, notification_type: str, 
                                       users: List["User"]) -> List["User"]:
        """Фильтрует пользователей, которым нужно отправить уведомление."""
        from models.user import User
        
        filtered_users = []
        
        for user in users:
            if await self.should_send_notification(user.id, notification_type):
                filtered_users.append(user)
        
        return filtered_users