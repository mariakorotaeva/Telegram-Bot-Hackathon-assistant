"""
Репозиторий для работы с настройками уведомлений.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from models.notification_settings import NotificationSettings
from config.database import get_db


class NotificationSettingsRepository:
    """Репозиторий для работы с настройками уведомлений."""
    
    def __init__(self): ...
    
    async def get_by_user_id(self, user_id: int) -> Optional[NotificationSettings]:
        """Находит настройки уведомлений пользователя."""
        stmt = select(NotificationSettings).where(NotificationSettings.user_id == user_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_or_create_settings(self, user_id: int) -> NotificationSettings:
        """Получает или создаёт настройки пользователя."""
        settings = await self.get_by_user_id(user_id)
        
        if not settings:
            settings = NotificationSettings(
                user_id=user_id,
                enabled=True,
                reminder_minutes=[5, 15, 60],
                new_event_enabled=True,
                event_updated_enabled=True,
                event_cancelled_enabled=True
            )
            await self.save(settings)
        
        return settings
    
    async def save(self, settings: NotificationSettings) -> NotificationSettings:
        """Сохраняет настройки уведомлений."""
        async with get_db() as session:
            session.add(settings)
            await session.commit()
            await session.refresh(settings)
            return settings
    
    async def toggle_enabled(self, user_id: int) -> NotificationSettings:
        """Переключает общую доступность уведомлений."""
        settings = await self.get_or_create_settings(user_id)
        settings.enabled = not settings.enabled
        return await self.save(settings)
    
    async def update_reminder_times(self, user_id: int, reminder_minutes: List[int]) -> NotificationSettings:
        """Обновляет время напоминаний."""
        settings = await self.get_or_create_settings(user_id)
        settings.reminder_minutes = sorted(reminder_minutes)
        return await self.save(settings)
    
    async def toggle_new_events(self, user_id: int) -> NotificationSettings:
        """Переключает уведомления о новых событиях."""
        settings = await self.get_or_create_settings(user_id)
        settings.new_event_enabled = not settings.new_event_enabled
        return await self.save(settings)
    
    async def toggle_event_updates(self, user_id: int) -> NotificationSettings:
        """Переключает уведомления об изменениях событий."""
        settings = await self.get_or_create_settings(user_id)
        settings.event_updated_enabled = not settings.event_updated_enabled
        return await self.save(settings)
    
    async def toggle_event_cancelled(self, user_id: int) -> NotificationSettings:
        """Переключает уведомления об отмене событий."""
        settings = await self.get_or_create_settings(user_id)
        settings.event_cancelled_enabled = not settings.event_cancelled_enabled
        return await self.save(settings)