# models/user.py
"""
Модель пользователя (участника) для базы данных.
Соответствует требованиям из документации.
"""

from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, Text, ARRAY, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum
from typing import Optional, List

from config.database import Base


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
    Требование из документации: "Текущий статус (в команде / ищет команду)"
    """
    LOOKING_FOR_TEAM = "looking_for_team"  # Ищет команду (по умолчанию)
    IN_TEAM = "in_team"  # Уже в команде
    NOT_LOOKING = "not_looking"  # Не ищет команду (например, хочет работать один)


# ============================================
# МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ (ТАБЛИЦА users)
# ============================================

class User(Base):
    """
    Модель пользователя.
    Каждый объект этого класса = одна строка в таблице 'users'.
    """

    # Имя таблицы в базе данных
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

    # ==================== ВНЕШНИЕ КЛЮЧИ ====================

    # ID команды, в которой состоит пользователь (если есть)
    # Ссылается на таблицу teams, поле id
    team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL")
    )

    # ==================== НАСТРОЙКИ И МЕТАДАННЫЕ ====================

    # Часовой пояс пользователя (для уведомлений)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC+3")

    # Активен ли пользователь (мягкое удаление)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время регистрации (автоматически при создании)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ==================== СВЯЗИ (RELATIONSHIPS) ====================

    # Команда, в которой состоит пользователь
    team: Mapped[Optional["Team"]] = relationship(
        "Team",
        back_populates="members"
    )

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

    # Команды, где пользователь является капитаном
    # (обратная ссылка из Team.captain)

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
            "team_id": self.team_id,

            # Метаданные
            "timezone": self.timezone,
            "is_active": self.is_active,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None
        }

    def is_looking_for_team(self) -> bool:
        """Проверяет, ищет ли пользователь команду."""
        return self.participant_status == ParticipantStatus.LOOKING_FOR_TEAM

    def is_in_team(self) -> bool:
        """Проверяет, состоит ли пользователь в команде."""
        return self.participant_status == ParticipantStatus.IN_TEAM

    def has_team(self) -> bool:
        """Проверяет, есть ли у пользователя команда (по team_id)."""
        return self.team_id is not None

    def join_team(self, team_id: int) -> None:
        """Добавляет пользователя в команду."""
        self.participant_status = ParticipantStatus.IN_TEAM
        self.team_id = team_id

    def leave_team(self) -> None:
        """Удаляет пользователя из команды."""
        self.participant_status = ParticipantStatus.LOOKING_FOR_TEAM
        self.team_id = None

    def update_skills(self, new_skills: List[str]) -> None:
        """Обновляет список навыков пользователя."""
        self.skills = new_skills

    def add_skill(self, skill: str) -> None:
        """Добавляет навык в список."""
        if not self.skills:
            self.skills = []
        if skill not in self.skills:
            self.skills.append(skill)

    def update_interests(self, new_interests: List[str]) -> None:
        """Обновляет список интересов пользователя."""
        self.interests = new_interests

    def add_interest(self, interest: str) -> None:
        """Добавляет интерес в список."""
        if not self.interests:
            self.interests = []
        if interest not in self.interests:
            self.interests.append(interest)

    def get_profile_summary(self) -> str:
        """Возвращает краткое описание профиля."""
        summary = f"{self.full_name}"

        if self.desired_role:
            summary += f" | {self.desired_role}"

        if self.skills:
            summary += f"\nНавыки: {', '.join(self.skills[:3])}"
            if len(self.skills) > 3:
                summary += f" и ещё {len(self.skills) - 3}"

        if self.bio and len(self.bio) > 0:
            bio_preview = self.bio[:100] + "..." if len(self.bio) > 100 else self.bio
            summary += f"\n\n{bio_preview}"

        return summary

    @classmethod
    def create_participant(cls, telegram_id: int, full_name: str, username: Optional[str] = None) -> "User":
        """
        Создаёт нового участника (фабричный метод).

        Args:
            telegram_id: ID пользователя в Telegram
            full_name: Полное имя
            username: Имя пользователя в Telegram (опционально)

        Returns:
            Новый объект User с ролью PARTICIPANT
        """
        return cls(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=UserRole.PARTICIPANT
        )

    @classmethod
    def create_organizer(cls, telegram_id: int, full_name: str, username: Optional[str] = None) -> "User":
        """Создаёт нового организатора."""
        return cls(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=UserRole.ORGANIZER
        )