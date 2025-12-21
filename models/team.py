"""
Модель команды для хакатона.
"""
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List

from config.database import Base


class Team(Base):
    """
    Модель команды.
    """
    
    __tablename__ = "teams"
    
    # Основные поля
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # Название команды
    
    # Внешние ключи
    captain_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )  # Капитан команды
    
    mentor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )  # Ментор команды (назначается организатором)
    
    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    captain: Mapped["User"] = relationship(
        "User",
        foreign_keys="[Team.captain_id]",
        back_populates="captained_teams"
    )
    
    mentor: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys="[Team.mentor_id]"
    )
    
    members: Mapped[List["User"]] = relationship(
        "User",
        back_populates="team",
        foreign_keys="[User.team_id]"
    )
    
    # Приглашения в команду
    invitations: Mapped[List["TeamInvitation"]] = relationship(
        "TeamInvitation",
        back_populates="team",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}', captain_id={self.captain_id})>"
    
    @property
    def member_count(self) -> int:
        """Количество участников в команде."""
        return len(self.members) if self.members else 0
    
    @property
    def is_full(self) -> bool:
        """Проверяет, полная ли команда (макс 5 человек)."""
        return self.member_count >= 5  # Обычно в хакатонах до 5 человек
    
    def add_member(self, user: "User") -> bool:
        """Добавляет участника в команду."""
        if self.is_full:
            return False
        
        if user not in self.members:
            user.team_id = self.id
            return True
        return False
    
    def remove_member(self, user: "User") -> bool:
        """Удаляет участника из команды."""
        if user in self.members:
            user.team_id = None
            return True
        return False
    
    def has_member(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь участником команды."""
        return any(member.id == user_id for member in self.members)
    
    def is_captain(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь капитаном команды."""
        return self.captain_id == user_id
    
    def is_mentor(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь ментором команды."""
        return self.mentor_id == user_id
    
    def can_join(self, user: "User") -> bool:
        """Проверяет, может ли пользователь присоединиться к команде."""
        if self.is_full:
            return False
        
        if user.team_id is not None:
            return False
        
        if user.id == self.captain_id:
            return False
        
        return True