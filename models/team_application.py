# models/team_application.py
"""
Модель заявки в команду (таблица team_applications).
Управляет процессом подачи заявок участниками в команды.
"""

from sqlalchemy import String, Enum as SQLEnum, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum
from typing import Optional

from config.database import Base


class ApplicationStatus(str, enum.Enum):
    """
    Статусы заявки в команду.
    """
    PENDING = "pending"  # Ожидает рассмотрения
    ACCEPTED = "accepted"  # Принята
    REJECTED = "rejected"  # Отклонена
    CANCELLED = "cancelled"  # Отозвана участником


class TeamApplication(Base):
    """
    Модель заявки в команду.
    """

    __tablename__ = "team_applications"

    # ============= ОСНОВНЫЕ ДАННЫЕ =============

    id: Mapped[int] = mapped_column(primary_key=True)

    # ============= ЗАЯВИТЕЛЬ И КОМАНДА =============

    # Кто подаёт заявку (ссылка на users.id)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # В какую команду (ссылка на teams.id)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False
    )

    # ============= СООБЩЕНИЕ ОТ ЗАЯВИТЕЛЯ =============

    # Почему участник хочет вступить в команду
    message: Mapped[Optional[str]] = mapped_column(Text)

    # ============= СТАТУС ЗАЯВКИ =============

    # Текущий статус заявки
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus),
        default=ApplicationStatus.PENDING
    )

    # ============= ДАТЫ =============

    # Когда подана заявка
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Когда рассмотрена (если рассмотрена)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # ============= ОТВЕТ КОМАНДЫ =============

    # Сообщение от команды (при принятии/отклонении)
    response_message: Mapped[Optional[str]] = mapped_column(Text)

    # ============= СВЯЗИ (RELATIONSHIPS) =============

    # Пользователь, подавший заявку
    user: Mapped["User"] = relationship(
        "User",
        back_populates="team_applications"
    )

    # Команда, в которую подана заявка
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="applications"
    )

    # ============= МЕТОДЫ ДЛЯ УДОБСТВА =============

    def __repr__(self) -> str:
        return f"<TeamApplication(id={self.id}, user_id={self.user_id}, team_id={self.team_id}, status='{self.status.value}')>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "message": self.message,
            "status": self.status.value,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "response_message": self.response_message
        }

    def accept(self, response_message: Optional[str] = None) -> None:
        """Принять заявку."""
        self.status = ApplicationStatus.ACCEPTED
        self.response_message = response_message
        self.reviewed_at = datetime.utcnow()

    def reject(self, response_message: Optional[str] = None) -> None:
        """Отклонить заявку."""
        self.status = ApplicationStatus.REJECTED
        self.response_message = response_message
        self.reviewed_at = datetime.utcnow()

    def cancel(self) -> None:
        """Отозвать заявку (только для пользователя)."""
        self.status = ApplicationStatus.CANCELLED
        self.reviewed_at = datetime.utcnow()