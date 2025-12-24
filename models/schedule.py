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

class EventVisibilityEnum(str, enum.Enum):
    ALL = "all"
    PARTICIPANT = "participant"
    ORGANIZER = "organizer" 
    MENTOR = "mentor"
    VOLUNTEER = "volunteer"


class EventChangeType(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    CANCELLED = "cancelled"


class Event(Base):

    __tablename__ = "events"

    #ОСНОВНОЕ
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(200))

    visibility: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    #СВЯЗИ

    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    creator_timezone: Mapped[str] = mapped_column(String(10), default="UTC+3")

    creator: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="created_events",
        foreign_keys=[created_by]
    )

    logs: Mapped[List["EventLog"]] = relationship(
        "EventLog",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    notifications: Mapped[List["EventNotification"]] = relationship(
        "EventNotification",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    #МЕТОДЫ

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title='{self.title}', start='{self.start_time}')>"

    def to_dict(self, user_timezone: str = "UTC+3", convert_datetimes: bool = False) -> Dict[str, Any]:
        """Преобразует объект события в словарь."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if convert_datetimes else self.start_time,
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if convert_datetimes else self.end_time,
            "location": self.location,
            "visibility": self.visibility,
            "created_by": self.created_by,
            "creator_timezone": self.creator_timezone,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if convert_datetimes else self.created_at,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if convert_datetimes else self.updated_at,
            "is_active": self.is_active
        }


class EventLog(Base):
    """Модель для логирования изменений событий."""

    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )
    changed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    change_type: Mapped[EventChangeType] = mapped_column(
        SQLEnum(EventChangeType),
        nullable=False
    )
    changes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    event: Mapped["Event"] = relationship(
        "Event",
        back_populates="logs"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[changed_by]
    )

    def __repr__(self) -> str:
        return f"<EventLog(id={self.id}, event_id={self.event_id}, type='{self.change_type}')>"


class EventNotification(Base):


    __tablename__ = "event_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


    user: Mapped["User"] = relationship(
        "User",
        back_populates="event_notifications"
    )
    event: Mapped["Event"] = relationship(
        "Event",
        back_populates="notifications"
    )

    def __repr__(self) -> str:
        return f"<EventNotification(id={self.id}, user_id={self.user_id}, event_id={self.event_id})>"