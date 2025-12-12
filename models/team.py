# models/team.py
"""
Модель команды (таблица teams).
Соответствует требованиям из документации.
"""

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List

from config.database import Base


class Team(Base):
    """
    Модель команды.
    Каждая команда = группа участников, работающих вместе над проектом.
    """

    __tablename__ = "teams"

    # ==================== ОСНОВНАЯ ИНФОРМАЦИЯ ====================

    # Первичный ключ
    id: Mapped[int] = mapped_column(primary_key=True)

    # Название команды (обязательное)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Описание команды (чем занимаетесь, что ищете)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # ==================== ТЕМАТИКА ПРОЕКТА ====================
    # Требование: "Тематика проекта (если определена)"

    project_theme: Mapped[Optional[str]] = mapped_column(String(200))
    # Пример: "AI-ассистент для образования", "FinTech мобильное приложение"

    # ==================== СОСТАВ КОМАНДЫ ====================
    # Требования:
    # - "Текущий состав (количество участников)"
    # - "Количество свободных мест"

    # Максимальное количество участников в команде
    max_members: Mapped[int] = mapped_column(Integer, default=5)

    # Текущее количество участников (будем обновлять автоматически)
    current_members_count: Mapped[int] = mapped_column(Integer, default=0)

    # ==================== НЕОБХОДИМЫЕ РОЛИ ====================
    # Требование: "Необходимые/нехватающие роли"

    # Какие роли нужны команде (массив строк)
    needed_roles: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(100)))
    # Пример: ["frontend developer", "designer", "backend developer"]

    # ==================== КОНТАКТЫ ====================
    # Требование: "Контакт для связи"

    # Дополнительная контактная информация
    contact_info: Mapped[Optional[str]] = mapped_column(String(200))
    # Пример: "@team_captain_telegram", "team@email.com"

    # ==================== СТАТУС И МЕТАДАННЫЕ ====================

    # Активна ли команда (мягкое удаление)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Заполнена ли команда (автоматически вычисляется)
    is_full: Mapped[bool] = mapped_column(Boolean, default=False)

    # Дата создания команды
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата последнего обновления
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # ==================== ВНЕШНИЕ КЛЮЧИ ====================

    # ID капитана команды (пользователь, который создал команду)
    # Ссылается на таблицу users
    captain_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # ==================== СВЯЗИ (RELATIONSHIPS) ====================

    # Капитан команды (связь с моделью User)
    captain: Mapped["User"] = relationship(
        "User",
        foreign_keys=[captain_id],
        backref="captained_teams"  # Обратная ссылка из User
    )

    # Участники команды (связь с моделью User)
    # Пока закомментируем, добавим позже, когда обновим модель User
    # members: Mapped[List["User"]] = relationship(
    #     "User",
    #     back_populates="team"
    # )

    # ==================== МЕТОДЫ ДЛЯ УДОБСТВА ====================

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}', members={self.current_members_count}/{self.max_members})>"

    def to_dict(self) -> dict:
        """Преобразует объект команды в словарь (для API)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "project_theme": self.project_theme,
            "max_members": self.max_members,
            "current_members_count": self.current_members_count,
            "needed_roles": self.needed_roles or [],
            "contact_info": self.contact_info,
            "is_active": self.is_active,
            "is_full": self.is_full,
            "captain_id": self.captain_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def update_members_count(self, actual_count: int) -> None:
        """
        Обновляет количество участников и статус заполненности.

        Args:
            actual_count: Фактическое количество участников в команде
        """
        self.current_members_count = actual_count
        self.is_full = actual_count >= self.max_members

    def has_free_slots(self) -> bool:
        """Проверяет, есть ли в команде свободные места."""
        return self.current_members_count < self.max_members

    def free_slots_count(self) -> int:
        """Возвращает количество свободных мест в команде."""
        return max(0, self.max_members - self.current_members_count)

    def needs_role(self, role: str) -> bool:
        """Проверяет, нужна ли команде указанная роль."""
        if not self.needed_roles:
            return False
        return role.lower() in [r.lower() for r in self.needed_roles]

    applications: Mapped[List["TeamApplication"]] = relationship(
        "TeamApplication",
        back_populates="team",
        cascade="all, delete-orphan"  # при удалении команды удаляются её заявки
    )

    captain: Mapped["User"] = relationship(
            "User",
            foreign_keys=[captain_id],  # ← ВАЖНО!
            back_populates="captained_teams"
    )

    # Участники команды (обратная ссылка из User.team)
    members: Mapped[List["User"]] = relationship(
            "User",
            back_populates="team",
            foreign_keys="[User.team_id]"  # ← ВАЖНО!
    )

    # Заявки в команду
    applications: Mapped[List["TeamApplication"]] = relationship(
            "TeamApplication",
            back_populates="team",
            cascade="all, delete-orphan",
            foreign_keys="[TeamApplication.team_id]"  # ← ВАЖНО!
    )