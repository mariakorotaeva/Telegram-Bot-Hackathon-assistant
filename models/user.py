from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, Text, ARRAY, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from typing import Optional, List

from config.database import Base


class UserRole(str, enum.Enum):
    PARTICIPANT = "participant"
    ORGANIZER = "organizer"
    MENTOR = "mentor"
    VOLUNTEER = "volunteer"


class ParticipantStatus(str, enum.Enum):
    LOOKING_FOR_TEAM = "looking_for_team"
    IN_TEAM = "in_team"
    NOT_LOOKING = "not_looking"


class User(Base):

    __tablename__ = "users"

    #ОСНОВНОЕ
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC+3")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    participant_status: Mapped[Optional[ParticipantStatus]] = mapped_column(
        SQLEnum(ParticipantStatus),
        default=ParticipantStatus.LOOKING_FOR_TEAM  # По умолчанию ищет команду
    )

    #ДЛЯ АНКЕТЫ

    profile_text: Mapped[Optional[str]] = mapped_column(Text, default="")
    profile_active: Mapped[bool] = mapped_column(Boolean, default=False)

    #ВНЕШНИЕ КЛЮЧИ

    team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL")
    )

    #СВЯЗИ

    created_events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="creator"
    )

    event_notifications: Mapped[List["EventNotification"]] = relationship(
        "EventNotification",
        back_populates="user"
    )

    team: Mapped[Optional["Team"]] = relationship(
            "Team",
            back_populates="members",
            foreign_keys="[User.team_id]"  # ← ВАЖНО!
    )

    captained_teams: Mapped[List["Team"]] = relationship(
        "Team",
        foreign_keys="[Team.captain_id]",
        back_populates="captain"
    )

    mentored_teams: Mapped[List["Team"]] = relationship(
        "Team",
        foreign_keys="[Team.mentor_id]",
        back_populates="mentor"
    )

    #НЕЧТО ДЛЯ "УДОБСТВА", ХОЧЕТСЯ УДАЛИТЬ

    # def __repr__(self) -> str:
    #     return f"<User(id={self.id}, telegram_id={self.telegram_id}, name='{self.full_name}')>"

    # def to_dict(self) -> dict:
    #     return {
    #         # Основные данные
    #         "id": self.id,
    #         "telegram_id": self.telegram_id,
    #         "username": self.username,
    #         "full_name": self.full_name,
    #         "role": self.role.value,

    #         # Контактная информация
    #         "email": self.email,
    #         "phone": self.phone,
    #         "telegram_username": self.telegram_username,

    #         # Анкета участника
    #         "desired_role": self.desired_role,
    #         "skills": self.skills or [],  # Если None, возвращаем пустой список
    #         "interests": self.interests or [],
    #         "experience": self.experience,
    #         "bio": self.bio,

    #         # Статус
    #         "participant_status": self.participant_status.value if self.participant_status else None,
    #         "team_id": self.team_id,

    #         # Метаданные
    #         "timezone": self.timezone,
    #         "is_active": self.is_active,
    #         "registered_at": self.registered_at.isoformat() if self.registered_at else None
    #     }

    #МЕТОДЫ ДЛЯ ПОИСКА КОМАНДЫ

    def is_looking_for_team(self) -> bool:
        """Проверяет, ищет ли пользователь команду."""
        return self.participant_status == ParticipantStatus.LOOKING_FOR_TEAM

    def is_in_team(self) -> bool:
        """Проверяет, состоит ли пользователь в команде."""
        return self.participant_status == ParticipantStatus.IN_TEAM

    def has_team(self) -> bool:
        """Проверяет, есть ли у пользователя команда."""
        return self.team_id is not None

    def join_team(self, team_id: int) -> None:
        """Добавляет пользователя в команду."""
        self.participant_status = ParticipantStatus.IN_TEAM
        self.team_id = team_id

    def leave_team(self) -> None:
        """Удаляет пользователя из команды."""
        self.participant_status = ParticipantStatus.LOOKING_FOR_TEAM
        self.team_id = None

    #ЧТО ЭТО????

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

    #МЕТОДЫ ДЛЯ АНКЕТ
    
    def is_profile_active(self) -> bool:
        """Проверяет, активна ли анкета."""
        return self.profile_active
    
    def is_profile_empty(self) -> bool:
        """Проверяет, пустая ли анкета."""
        return not self.profile_text or not self.profile_text.strip()
    
    def can_activate_profile(self) -> bool:
        """Проверяет, может ли пользователь активировать анкету."""
        return not self.has_team() and not self.is_profile_empty()
    
    def update_profile(self, text: str) -> None:
        """Обновляет текст анкеты."""
        self.profile_text = text
    
    def set_profile_active(self, active: bool) -> bool:
        """Устанавливает статус активности анкеты."""
        if active and self.has_team():
            return False
        
        if active and self.is_profile_empty():
            return False
            
        self.profile_active = active
        return True
    
    # def get_profile_preview(self, max_length: int = 100) -> str:
    #     """Возвращает превью анкеты."""
    #     if self.is_profile_empty():
    #         return "Анкета пустая"
        
    #     text = self.profile_text.strip()
    #     if len(text) <= max_length:
    #         return text
        
    #     return text[:max_length] + "..."
    
    def get_full_profile(self) -> str:
        """Возвращает полную анкету."""
        if self.is_profile_empty():
            return ""
        
        return self.profile_text.strip()
