# models/event.py
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
from config.database import Base  # или from models.base import Base


class EventType(str, enum.Enum):
    LECTURE = "lecture"
    WORKSHOP = "workshop"
    HACKING = "hacking"
    BREAK = "break"
    FOOD = "food"
    CEREMONY = "ceremony"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[EventType] = mapped_column(SQLEnum(EventType))
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    location: Mapped[str | None] = mapped_column(String(100))
    speaker: Mapped[str | None] = mapped_column(String(200))