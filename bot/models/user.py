# models/user.py
from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum

# Импортируем Base из config/database.py или models/base.py
from models.database import Base  # или from models.base import Base


class UserRole(str, enum.Enum):
    PARTICIPANT = "participant"
    ORGANIZER = "organizer"
    MENTOR = "mentor"
    VOLUNTEER = "volunteer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC+3")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)