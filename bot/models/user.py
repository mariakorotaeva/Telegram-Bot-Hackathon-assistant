# models/user.py
"""
Модель пользователя (таблица users).
Хранит информацию обо всех пользователях бота.
"""

from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, Text, ARRAY, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum
from typing import Optional, List

from bot.config.database import Base  # базовый класс для всех моделей


# ============================================
# ПЕРЕЧИСЛЕНИЯ (ENUMS) - фиксированные наборы значений
# ============================================

class UserRole(str, enum.Enum):
    """
    Роли пользователей в системе.
    Используем str в качестве базового типа для удобства сериализации.
    """
    PARTICIPANT = "participant"  # Участник хакатона
    ORGANIZER = "organizer"  # Организатор
    MENTOR = "mentor"  # Ментор
    VOLUNTEER = "volunteer"  # Волонтёр


class ParticipantStatus(str, enum.Enum):
    """
    Статус участника относительно поиска команды.
    """
    LOOKING_FOR_TEAM = "looking_for_team"  # Ищет команду
    IN_TEAM = "in_team"  # Уже в команде
    NOT_LOOKING = "not_looking"  # Не ищет команду


# ============================================
# МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ (ТАБЛИЦА users)
# ============================================

class User(Base):
    """
    Модель пользователя.
    Каждый экземпляр этого класса = одна строка в таблице users.
    """

    # Имя таблицы в базе данных
    __tablename__ = "users"

    # ============= ОСНОВНЫЕ ДАННЫЕ =============

    # Первичный ключ - уникальный идентификатор
    id: Mapped[int] = mapped_column(primary_key=True)

    # Уникальный ID пользователя в Telegram
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)

    # Имя пользователя в Telegram (без @)
    username: Mapped[Optional[str]] = mapped_column(String(100))

    # Полное имя пользователя
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Роль пользователя в системе
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False)

    # ============= КОНТАКТНАЯ ИНФОРМАЦИЯ =============

    # Email пользователя
    email: Mapped[Optional[str]] = mapped_column(String(100))

    # Телефон пользователя
    phone: Mapped[Optional[str]] = mapped_column(String(20))

    # Имя пользователя в Telegram (для контакта)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100))

    # ============= ДЛЯ УЧАСТНИКОВ - АНКЕТА =============

    # Желаемая роль в команде (например: "бэкенд-разработчик", "дизайнер")
    desired_role: Mapped[Optional[str]] = mapped_column(String(100))

    # Навыки и экспертиза (массив строк)
    # Пример: ["Python", "FastAPI", "PostgreSQL"]
    skills: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(100)))

    # Интересы по темам (массив строк)
    # Пример: ["AI", "Web Development", "Mobile Apps"]
    interests: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(100)))

    # Опыт работы/участия в хакатонах
    experience: Mapped[Optional[str]] = mapped_column(Text)

    # О себе (краткое описание)
    bio: Mapped[Optional[str]] = mapped_column(Text)

    # ============= СТАТУС УЧАСТНИКА =============

    # Статус поиска команды (только для участников)
    participant_status: Mapped[Optional[ParticipantStatus]] = mapped_column(
        SQLEnum(ParticipantStatus),
        default=ParticipantStatus.LOOKING_FOR_TEAM
    )

    # ============= НАСТРОЙКИ =============

    # Часовой пояс пользователя (для уведомлений)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC+3")

    # Активен ли пользователь (мягкое удаление)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время регистрации
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ============= ВНЕШНИЕ КЛЮЧИ =============

    # ID команды, в которой состоит пользователь (если есть)
    # Ссылается на таблицу teams, поле id
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"))

    # ============= СВЯЗИ (RELATIONSHIPS) =============

    # Связь с командой (если пользователь в команде)
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="members")

    # Все заявки, которые подавал пользователь
    team_applications: Mapped[List["TeamApplication"]] = relationship(
        "TeamApplication",
        back_populates="user",
        cascade="all, delete-orphan"  # при удалении пользователя удаляются его заявки
    )

    # Все уведомления пользователя
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # ============= МЕТОДЫ КЛАССА =============

    def __repr__(self) -> str:
        """Строковое представление объекта (для отладки)."""
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, name='{self.full_name}')>"

    def to_dict(self) -> dict:
        """Преобразование объекта в словарь (для API)."""
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role.value,
            "email": self.email,
            "phone": self.phone,
            "desired_role": self.desired_role,
            "skills": self.skills or [],
            "interests": self.interests or [],
            "participant_status": self.participant_status.value if self.participant_status else None,
            "team_id": self.team_id,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None
        }