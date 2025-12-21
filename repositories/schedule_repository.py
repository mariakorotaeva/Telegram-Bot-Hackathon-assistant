# repositories/schedule_repository.py
"""
Репозиторий для работы с расписанием (Data Access Layer).
Содержит низкоуровневые операции с БД для событий, логов и уведомлений.
"""

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from models.schedule import Event, EventLog, EventNotification, EventChangeType
from models.user import User, UserRole
from config.database import get_db


class ScheduleRepository:
    """Репозиторий для работы с расписанием."""

    def __init__(self): ...

    # ==================== МЕТОДЫ ДЛЯ СОБЫТИЙ ====================

    async def create_event(self, event: Event) -> Event:
        """Создаёт новое событие."""
        async with get_db() as session:
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event

    async def get_event_by_id(self, event_id: int) -> Optional[Event]:
        """Находит событие по ID."""
        stmt = select(Event).where(Event.id == event_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_event(self, event_id: int, **kwargs) -> bool:
        """Обновляет данные события."""
        stmt = (
            update(Event)
            .where(Event.id == event_id)
            .values(**kwargs, updated_at=datetime.utcnow())
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def delete_event_soft(self, event_id: int) -> bool:
        """Удаляет событие (мягкое удаление)."""
        return await self.update_event(event_id, is_active=False)

    async def delete_event_hard(self, event_id: int) -> bool:
        """Удаляет событие (жесткое удаление)."""
        stmt = delete(Event).where(Event.id == event_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def get_all_events(self, include_inactive: bool = False) -> List[Event]:
        """Возвращает все события."""
        stmt = select(Event).order_by(Event.start_time)
        if not include_inactive:
            stmt = stmt.where(Event.is_active == True)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_events_for_role(
        self, 
        role: str, 
        user_timezone: str = "UTC+3",
        include_all: bool = True
    ) -> List[Event]:
        """Возвращает события, видимые для указанной роли."""
        # Базовый запрос для активных событий
        stmt = select(Event).where(Event.is_active == True).order_by(Event.start_time)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            events = result.scalars().all()
            
            # Фильтруем по видимости на уровне Python
            filtered_events = []
            for event in events:
                if include_all and "all" in event.visibility:
                    filtered_events.append(event)
                elif role in event.visibility:
                    filtered_events.append(event)
            
            return filtered_events

    async def get_upcoming_events(
        self, 
        hours_ahead: int = 24, 
        role: Optional[str] = None
    ) -> List[Event]:
        """Возвращает ближайшие события."""
        now = datetime.utcnow()
        time_threshold = now + timedelta(hours=hours_ahead)
        
        stmt = select(Event).where(
            and_(
                Event.is_active == True,
                Event.start_time >= now,
                Event.start_time <= time_threshold
            )
        ).order_by(Event.start_time)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            events = result.scalars().all()
            
            if role:
                # Фильтруем по роли если указана
                events = [e for e in events if self._is_visible_for_role(e, role)]
            
            return events

    async def get_active_events_now(self) -> List[Event]:
        """Возвращает события, которые идут прямо сейчас."""
        now = datetime.utcnow()
        stmt = select(Event).where(
            and_(
                Event.is_active == True,
                Event.start_time <= now,
                Event.end_time >= now
            )
        ).order_by(Event.start_time)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_events_by_creator(self, user_id: int) -> List[Event]:
        """Возвращает события, созданные пользователем."""
        stmt = select(Event).where(
            and_(
                Event.created_by == user_id,
                Event.is_active == True
            )
        ).order_by(Event.start_time.desc())
        
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def search_events(
        self, 
        query: str, 
        role: Optional[str] = None
    ) -> List[Event]:
        """Ищет события по названию и описанию."""
        search_term = f"%{query.lower()}%"
        stmt = select(Event).where(
            and_(
                Event.is_active == True,
                or_(
                    Event.title.ilike(search_term),
                    Event.description.ilike(search_term),
                    Event.location.ilike(search_term)
                )
            )
        ).order_by(Event.start_time)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            events = result.scalars().all()
            
            if role:
                # Фильтруем по роли если указана
                events = [e for e in events if self._is_visible_for_role(e, role)]
            
            return events

    # ==================== МЕТОДЫ ДЛЯ ЛОГОВ ====================

    async def create_event_log(self, event_log: EventLog) -> EventLog:
        """Создаёт запись в логе событий."""
        async with get_db() as session:
            session.add(event_log)
            await session.commit()
            await session.refresh(event_log)
            return event_log

    async def get_event_logs(self, event_id: int) -> List[EventLog]:
        """Возвращает логи изменений для события."""
        stmt = select(EventLog).where(
            EventLog.event_id == event_id
        ).order_by(EventLog.changed_at.desc())
        
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_recent_changes(
        self, 
        limit: int = 50, 
        user_id: Optional[int] = None
    ) -> List[EventLog]:
        """Возвращает последние изменения событий."""
        stmt = select(EventLog).order_by(EventLog.changed_at.desc()).limit(limit)
        
        if user_id:
            stmt = stmt.where(EventLog.changed_by == user_id)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    # ==================== МЕТОДЫ ДЛЯ УВЕДОМЛЕНИЙ ====================

    async def create_notification(self, notification: EventNotification) -> EventNotification:
        """Создаёт запись об уведомлении."""
        async with get_db() as session:
            session.add(notification)
            await session.commit()
            await session.refresh(notification)
            return notification

    async def get_user_notifications(
        self, 
        user_id: int, 
        unread_only: bool = False
    ) -> List[EventNotification]:
        """Возвращает уведомления пользователя."""
        stmt = select(EventNotification).where(
            EventNotification.user_id == user_id
        ).order_by(EventNotification.sent_at.desc())
        
        if unread_only:
            stmt = stmt.where(EventNotification.read_at.is_(None))
        
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def mark_notification_as_read(self, notification_id: int) -> bool:
        """Отмечает уведомление как прочитанное."""
        stmt = (
            update(EventNotification)
            .where(EventNotification.id == notification_id)
            .values(read_at=datetime.utcnow())
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def mark_all_notifications_as_read(self, user_id: int) -> bool:
        """Отмечает все уведомления пользователя как прочитанные."""
        stmt = (
            update(EventNotification)
            .where(
                and_(
                    EventNotification.user_id == user_id,
                    EventNotification.read_at.is_(None)
                )
            )
            .values(read_at=datetime.utcnow())
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def has_notification(
        self, 
        user_id: int, 
        event_id: int, 
        notification_type: str
    ) -> bool:
        """Проверяет, было ли уже отправлено такое уведомление."""
        stmt = select(EventNotification).where(
            and_(
                EventNotification.user_id == user_id,
                EventNotification.event_id == event_id,
                EventNotification.notification_type == notification_type
            )
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def _is_visible_for_role(self, event: Event, role: str) -> bool:
        """Проверяет, видно ли событие для указанной роли."""
        return "all" in event.visibility or role in event.visibility

    async def get_users_for_event(self, event: Event) -> List[User]:
        """Возвращает пользователей, которые должны видеть событие."""
        if "all" in event.visibility:
            # Все активные пользователи
            stmt = select(User).where(User.is_active == True)
        else:
            # Только пользователи с подходящими ролями
            stmt = select(User).where(
                and_(
                    User.is_active == True,
                    User.role.in_(event.visibility)
                )
            )
        
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()