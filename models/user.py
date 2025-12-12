# models/user.py
"""
Модель пользователя (участника) для базы данных.
Соответствует требованиям из документации.
"""

# 1. Импортируем необходимые типы из SQLAlchemy
from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, Text, ARRAY, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum  # Для создания перечислений (фиксированных наборов значений)
from typing import Optional, List  # Для указания типов (Optional = может быть None)

# 2. Импортируем наш базовый класс
from config.database import Base


# 3. СОЗДАЁМ ПЕРЕЧИСЛЕНИЯ (ENUMS) - фиксированные наборы значений

class UserRole(str, enum.Enum):
    """
    Роли пользователей в системе хакатона.
    Используем str в качестве базового типа для удобства работы с API.
    """
    PARTICIPANT = "participant"  # Участник хакатона (основная роль)
    ORGANIZER = "organizer"  # Организатор (может управлять ботом)
    MENTOR = "mentor"  # Ментор (помогает командам)
    VOLUNTEER = "volunteer"  # Волонтёр (помощник организаторов)


class ParticipantStatus(str, enum.Enum):
    """
    Статус участника относительно поиска команды.
    Требование из документации: "Текущий статус (в команде / ищет команду)"
    """
    LOOKING_FOR_TEAM = "looking_for_team"  # Ищет команду (по умолчанию)
    IN_TEAM = "in_team"  # Уже в команде
    NOT_LOOKING = "not_looking"  # Не ищет команду (например, хочет работать один)


# 4. СОЗДАЁМ МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ

class User(Base):
    """
    Модель пользователя.
    Каждый объект этого класса = одна строка в таблице 'users'.
    """

    # Указываем имя таблицы в базе данных
    __tablename__ = "users"

    # ==================== ОСНОВНЫЕ ДАННЫЕ ====================

    # Первичный ключ - уникальный идентификатор каждой записи
    id: Mapped[int] = mapped_column(primary_key=True)

    # Telegram ID пользователя (уникальный, обязательный)
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)

    # Имя пользователя в Telegram (без @)
    username: Mapped[Optional[str]] = mapped_column(String(100))

    # Полное имя пользователя (обязательное)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Роль пользователя в системе
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False)

    # ==================== КОНТАКТНАЯ ИНФОРМАЦИЯ ====================
    # Требование из документации: "Контактная информация"

    # Email пользователя
    email: Mapped[Optional[str]] = mapped_column(String(100))

    # Номер телефона
    phone: Mapped[Optional[str]] = mapped_column(String(20))

    # Telegram username для связи (может отличаться от username)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100))

    # ==================== АНКЕТА УЧАСТНИКА ====================
    # Все пункты из требований документации:

    # 1. Навыки и экспертиза
    # Используем ARRAY для хранения списка навыков
    skills: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(100)))
    # Пример: ["Python", "FastAPI", "PostgreSQL", "UI/UX Design"]

    # 2. Желаемая роль в команде
    desired_role: Mapped[Optional[str]] = mapped_column(String(100))
    # Пример: "Backend developer", "Designer", "Project manager"

    # 3. Интересы и предпочтения по темам
    interests: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(100)))
    # Пример: ["AI/ML", "Web Development", "Mobile Apps", "FinTech"]

    # 4. Опыт (дополнительное поле)
    experience: Mapped[Optional[str]] = mapped_column(Text)

    # 5. Краткое описание "О себе"
    bio: Mapped[Optional[str]] = mapped_column(Text)

    # ==================== СТАТУС УЧАСТНИКА ====================
    # Требование из документации: "Текущий статус (в команде / ищет команду)"

    participant_status: Mapped[Optional[ParticipantStatus]] = mapped_column(
        SQLEnum(ParticipantStatus),
        default=ParticipantStatus.LOOKING_FOR_TEAM  # По умолчанию ищет команду
    )

    # Внешний ключ на команду (если пользователь в команде)
    # Пока оставляем закомментированным, создадим позже
    # team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"))

    # ==================== НАСТРОЙКИ И МЕТАДАННЫЕ ====================

    # Часовой пояс пользователя (для уведомлений)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC+3")

    # Активен ли пользователь (мягкое удаление)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время регистрации (автоматически при создании)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ==================== МЕТОДЫ ДЛЯ УДОБСТВА ====================

    def __repr__(self) -> str:
        """
        Строковое представление объекта (для отладки).
        Показывается в консоли при выводе объекта.
        """
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, name='{self.full_name}')>"

    def to_dict(self) -> dict:
        """
        Преобразует объект пользователя в словарь.
        Полезно для API и передачи данных.
        """
        return {
            # Основные данные
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role.value,

            # Контактная информация
            "email": self.email,
            "phone": self.phone,
            "telegram_username": self.telegram_username,

            # Анкета участника
            "desired_role": self.desired_role,
            "skills": self.skills or [],  # Если None, возвращаем пустой список
            "interests": self.interests or [],
            "experience": self.experience,
            "bio": self.bio,

            # Статус
            "participant_status": self.participant_status.value if self.participant_status else None,

            # Метаданные
            "timezone": self.timezone,
            "is_active": self.is_active,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None
        }

    def is_looking_for_team(self) -> bool:
        """Проверяет, ищет ли пользователь команду."""
        return self.participant_status == ParticipantStatus.LOOKING_FOR_TEAM

    def join_team(self, team_id: int) -> None:
        """Добавляет пользователя в команду."""
        # Пока просто меняем статус, связь добавим позже
        self.participant_status = ParticipantStatus.IN_TEAM
        # self.team_id = team_id  # Раскомментируем, когда создадим модель Team

    def leave_team(self) -> None:
        """Удаляет пользователя из команды."""
        self.participant_status = ParticipantStatus.LOOKING_FOR_TEAM
        # self.team_id = None  # Раскомментируем, когда создадим модель Team