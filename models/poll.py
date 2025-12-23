# models/poll.py
"""
Модель опроса для организаторов.
"""

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from config.database import Base


class Poll(Base):
    """
    Модель опроса.
    Организаторы создают опросы, участники голосуют.
    """

    __tablename__ = "polls"

    # ==================== ОСНОВНЫЕ ДАННЫЕ ====================

    id: Mapped[int] = mapped_column(primary_key=True)

    # Внутренний ID опроса (можно использовать для ссылок)
    poll_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Текст вопроса
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # ==================== СОЗДАТЕЛЬ И ВРЕМЯ ====================

    # Кто создал опрос (ссылка на users.id)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Имя создателя (для быстрого доступа)
    creator_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Дата создания
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Активен ли опрос (можно закрывать)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ==================== ВАРИАНТЫ ОТВЕТОВ ====================

    # Варианты ответов храним в JSON
    # Формат: ["Вариант 1", "Вариант 2", "Вариант 3"]
    options: Mapped[List[str]] = mapped_column(JSON, nullable=False)

    # Общее количество голосов (для быстрого доступа)
    total_votes: Mapped[int] = mapped_column(Integer, default=0)

    # ==================== ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙК ====================

    # Анонимный ли опрос (не показывать кто как проголосовал)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)

    # Можно ли менять голос
    allow_multiple_votes: Mapped[bool] = mapped_column(Boolean, default=False)

    # Показывать ли результаты сразу
    show_results_immediately: Mapped[bool] = mapped_column(Boolean, default=True)

    # Категория опроса (общий, для команды, для трека и т.д.)
    category: Mapped[Optional[str]] = mapped_column(String(100))

    # Дата окончания опроса (если есть)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # ==================== СВЯЗИ ====================

    # Создатель опроса
    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])

    # Голоса в этом опросе
    votes: Mapped[List["PollVote"]] = relationship(
        "PollVote",
        back_populates="poll",
        cascade="all, delete-orphan"
    )

    # ==================== МЕТОДЫ ====================

    def __repr__(self) -> str:
        return f"<Poll(id={self.id}, question='{self.question[:30]}...', votes={self.total_votes})>"

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь для API."""
        return {
            "id": self.id,
            "poll_id": self.poll_id,
            "question": self.question,
            "creator_id": self.creator_id,
            "creator_name": self.creator_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
            "options": self.options,
            "total_votes": self.total_votes,
            "is_anonymous": self.is_anonymous,
            "allow_multiple_votes": self.allow_multiple_votes,
            "show_results_immediately": self.show_results_immediately,
            "category": self.category,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }

    def get_results(self) -> Dict[int, int]:
        """
        Возвращает результаты опроса.
        Формат: {индекс_варианта: количество_голосов}
        """
        results = {i: 0 for i in range(len(self.options))}

        for vote in self.votes:
            results[vote.option_index] = results.get(vote.option_index, 0) + 1

        return results

    def has_expired(self) -> bool:
        """Проверяет, истекло ли время опроса."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def can_vote(self) -> bool:
        """Можно ли голосовать в этом опросе."""
        return self.is_active and not self.has_expired()

    def format_results_for_display(self) -> str:
        """Форматирует результаты для отображения в боте."""
        results = self.get_results()
        total = sum(results.values())

        text = f"📊 <b>Результаты опроса</b>\n\n"
        text += f"<b>Вопрос:</b> {self.question}\n"
        text += f"<b>Всего голосов:</b> {total}\n"
        text += f"<b>Создатель:</b> {self.creator_name}\n"

        if total > 0:
            for i, option in enumerate(self.options):
                votes = results.get(i, 0)
                percentage = (votes / total) * 100 if total > 0 else 0

                # Создаем прогресс-бар
                bar_length = 20
                filled = int(percentage / 100 * bar_length)
                progress_bar = "█" * filled + "░" * (bar_length - filled)

                text += f"\n<b>{i + 1}. {option}</b>\n"
                text += f"{progress_bar} {votes} ({percentage:.1f}%)\n"
        else:
            text += "\nПока никто не проголосовал.\n"

        if self.has_expired():
            text += "\n⏰ <i>Опрос завершен</i>"
        elif not self.is_active:
            text += "\n🚫 <i>Опрос закрыт</i>"

        return text

class PollMessage(Base):
    __tablename__ = "pollmsgs"

    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[str] = mapped_column(
        ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    tg_poll_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    poll: Mapped["Poll"] = relationship("Poll", foreign_keys=[poll_id])