"""
Модель приглашения в команду.
"""
from sqlalchemy import Integer, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
import enum

from config.database import Base


class InvitationStatus(str, enum.Enum):
    """Статус приглашения."""
    PENDING = "pending"      # Ожидает ответа
    ACCEPTED = "accepted"    # Принято
    REJECTED = "rejected"    # Отклонено
    CANCELLED = "cancelled"  # Отменено капитаном


class TeamInvitation(Base):
    """
    Приглашение пользователя в команду.
    """
    
    __tablename__ = "team_invitations"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Внешние ключи
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False
    )
    
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    invited_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )  # Кто отправил приглашение (обычно капитан)
    
    # Статус приглашения
    status: Mapped[InvitationStatus] = mapped_column(
        SQLEnum(InvitationStatus),
        default=InvitationStatus.PENDING
    )
    
    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Связи
    team: Mapped["Team"] = relationship("Team", back_populates="invitations")
    
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys="[TeamInvitation.user_id]",
        back_populates="team_invitations"
    )
    
    invited_by: Mapped["User"] = relationship(
        "User",
        foreign_keys="[TeamInvitation.invited_by_id]"
    )
    
    def __repr__(self) -> str:
        return f"<TeamInvitation(id={self.id}, team_id={self.team_id}, user_id={self.user_id}, status={self.status})>"
    
    def accept(self) -> bool:
        """Принимает приглашение."""
        if self.status != InvitationStatus.PENDING:
            return False
        
        self.status = InvitationStatus.ACCEPTED
        self.responded_at = datetime.utcnow()
        
        # Добавляем пользователя в команду
        if self.team.can_join(self.user):
            self.user.team_id = self.team_id
            return True
        
        return False
    
    def reject(self) -> bool:
        """Отклоняет приглашение."""
        if self.status != InvitationStatus.PENDING:
            return False
        
        self.status = InvitationStatus.REJECTED
        self.responded_at = datetime.utcnow()
        return True
    
    def cancel(self) -> bool:
        """Отменяет приглашение (капитаном)."""
        if self.status != InvitationStatus.PENDING:
            return False
        
        self.status = InvitationStatus.CANCELLED
        self.responded_at = datetime.utcnow()
        return True
    
    def is_expired(self, hours: int = 24) -> bool:
        """Проверяет, истекло ли приглашение (по умолчанию 24 часа)."""
        if self.status != InvitationStatus.PENDING:
            return False
        
        time_passed = datetime.utcnow() - self.created_at
        return time_passed.total_seconds() > hours * 3600