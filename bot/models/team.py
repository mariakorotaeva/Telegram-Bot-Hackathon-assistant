# models/team.py
"""
Модель команды (таблица teams).
Хранит информацию о командах хакатона.
"""

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List

from bot.config.database import Base


class Team(Base):
    """
    Модель команды.
    """

    __tablename__ = "teams"

    # ============= ОСНОВНАЯ ИНФОРМАЦИЯ =============

    id: Mapped[int] = mapped_column(primary_key=True)

    # Название команды
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Описание команды (чем занимаетесь, что ищете)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Тематика проекта (если определена)
    project_theme: Mapped[Optional[str]] = mapped_column(String(200))

    # ============= СОСТАВ КОМАНДЫ =============

    # Максимальное количество участников
    max_members: Mapped[int] = mapped_column(Integer, default=5)

    # Текущее количество участников
    # Это вычисляемое поле - фактическое количество берётся из связи с users
    current_members_count: Mapped[int] = mapped_column(Integer, default=0)

    # ============= НЕОБХОДИМЫЕ/НЕХВАТАЮЩИЕ РОЛИ =============

    # Какие роли нужны команде (массив строк)
    # Пример: ["frontend developer", "designer", "project manager"]
    needed_roles: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(100)))

    # ============= КОНТАКТЫ =============

    # Контактная информация (если отличается от капитана)
    contact_info: Mapped[Optional[str]] = mapped_column(String(200))

    # ============= СТАТУС =============

    # Активна ли команда (мягкое удаление)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Заполнена ли команда (вычисляется автоматически)
    is_full: Mapped[bool] = mapped_column(Boolean, default=False)

    # Дата создания команды
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ============= ВНЕШНИЕ КЛЮЧИ =============

    # ID капитана команды (пользователь, который создал команду)
    captain_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    # ID контактного лица (может отличаться от капитана)
    contact_person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # ============= СВЯЗИ (RELATIONSHIPS) =============

    # Капитан команды
    captain: Mapped["User"] = relationship(
        "User",
        foreign_keys=[captain_id],
        backref="captained_teams"  # обратная ссылка на User
    )

    # Контактное лицо
    contact_person: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[contact_person_id]
    )

    # Участники команды
    members: Mapped[List["User"]] = relationship(
        "User",
        back_populates="team",
        foreign_keys="[User.team_id]"  # указываем, какое поле в User связывается
    )

    # Заявки в команду
    applications: Mapped[List["TeamApplication"]] = relationship(
        "TeamApplication",
        back_populates="team",
        cascade="all, delete-orphan"  # при удалении команды удаляются её заявки
    )

    # ============= МЕТОДЫ КЛАССА =============

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}', members={self.current_members_count}/{self.max_members})>"

    def to_dict(self) -> dict:
        """Преобразование объекта в словарь (для API)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "project_theme": self.project_theme,
            "max_members": self.max_members,
            "current_members_count": self.current_members_count,
            "needed_roles": self.needed_roles or [],
            "is_full": self.is_full,
            "captain_id": self.captain_id,
            "contact_person_id": self.contact_person_id,
            "contact_info": self.contact_info,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def update_members_count(self) -> None:
        """
        Обновляет количество участников и статус заполненности.
        Этот метод нужно вызывать при добавлении/удалении участников.
        """
        # Считаем фактическое количество участников
        actual_count = len([m for m in self.members if m.is_active])
        self.current_members_count = actual_count
        self.is_full = actual_count >= self.max_members