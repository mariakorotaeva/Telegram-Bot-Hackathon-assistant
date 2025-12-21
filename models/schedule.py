# models/schedule.py
"""
Модель расписания для базы данных.
Соответствует структуре из исходного кода.
"""

from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, Text, JSON, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import enum

from config.database import Base

# ============================================
# ПЕРЕЧИСЛЕНИЯ (ENUMS)
# ============================================

class EventVisibilityEnum(str, enum.Enum):
    """
    Типы видимости событий для разных ролей.
    Соответствует EventVisibility из исходного кода.
    """
    ALL = "all"           # Для всех
    PARTICIPANT = "participant"  # Участники
    ORGANIZER = "organizer"      # Организаторы
    MENTOR = "mentor"           # Менторы
    VOLUNTEER = "volunteer"     # Волонтеры


class EventChangeType(str, enum.Enum):
    """
    Типы изменений событий для логов.
    """
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    CANCELLED = "cancelled"


# ============================================
# МОДЕЛЬ СОБЫТИЯ (ТАБЛИЦА events)
# ============================================

class Event(Base):
    """
    Модель события в расписании.
    Каждый объект этого класса = одна строка в таблице 'events'.
    """

    __tablename__ = "events"

    # ==================== ОСНОВНЫЕ ДАННЫЕ ====================

    id: Mapped[int] = mapped_column(primary_key=True)

    # Название события (обязательное)
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # Описание события
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Время начала (обязательное)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Время окончания (обязательное)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Место проведения
    location: Mapped[Optional[str]] = mapped_column(String(200))

    # ==================== ВИДИМОСТЬ И ДОСТУП ====================
    # Храним массив ролей, для которых видно событие

    visibility: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list  # По умолчанию пустой список
    )
    # Пример: ["all"], ["participant", "mentor"], ["organizer"]

    # ==================== ВНЕШНИЕ КЛЮЧИ И СВЯЗИ ====================

    # Кто создал событие
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    # Часовой пояс создателя (для корректного отображения времени)
    creator_timezone: Mapped[str] = mapped_column(String(10), default="UTC+3")

    # ==================== МЕТАДАННЫЕ ====================

    # Дата и время создания
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Активно ли событие (для мягкого удаления)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время последнего обновления
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # ==================== СВЯЗИ (RELATIONSHIPS) ====================

    # Создатель события
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="created_events",
        foreign_keys=[created_by]
    )

    # Логи изменений этого события
    logs: Mapped[List["EventLog"]] = relationship(
        "EventLog",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    # Уведомления об этом событии
    notifications: Mapped[List["EventNotification"]] = relationship(
        "EventNotification",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    # ==================== МЕТОДЫ ====================

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title='{self.title}', start='{self.start_time}')>"

    def to_dict(self, user_timezone: str = "UTC+3") -> Dict[str, Any]:
        """Преобразует объект события в словарь."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "location": self.location,
            "visibility": self.visibility,
            "created_by": self.created_by,
            "creator_timezone": self.creator_timezone,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active
        }


# ============================================
# МОДЕЛЬ ЛОГА ИЗМЕНЕНИЙ СОБЫТИЙ
# ============================================

class EventLog(Base):
    """
    Модель для логирования изменений событий.
    """

    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Ссылка на событие
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )

    # Кто внес изменения
    changed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    # Тип изменения
    change_type: Mapped[EventChangeType] = mapped_column(
        SQLEnum(EventChangeType),
        nullable=False
    )

    # Изменения в формате JSON
    changes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    # Дата и время изменения
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ==================== СВЯЗИ ====================

    event: Mapped["Event"] = relationship(
        "Event",
        back_populates="logs"
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[changed_by]
    )

    # ==================== МЕТОДЫ ====================

    def __repr__(self) -> str:
        return f"<EventLog(id={self.id}, event_id={self.event_id}, type='{self.change_type}')>"


# ============================================
# МОДЕЛЬ УВЕДОМЛЕНИЙ О СОБЫТИЯХ
# ============================================

class EventNotification(Base):
    """
    Модель для отслеживания отправленных уведомлений о событиях.
    """

    __tablename__ = "event_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Пользователь, которому отправлено уведомление
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Событие, о котором уведомление
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False
    )

    # Тип уведомления
    notification_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # "new", "updated", "cancelled", "reminder"

    # Дата отправки
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата прочтения (если есть)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # ==================== СВЯЗИ ====================

    user: Mapped["User"] = relationship(
        "User",
        back_populates="event_notifications"
    )

    event: Mapped["Event"] = relationship(
        "Event",
        back_populates="notifications"
    )

    # ==================== МЕТОДЫ ====================

    def __repr__(self) -> str:
        return f"<EventNotification(id={self.id}, user_id={self.user_id}, event_id={self.event_id})>"