from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from config.database import Base


class PollVote(Base):

    __tablename__ = "poll_votes"

    #один пользователь - один голос в опросе
    __table_args__ = (
        UniqueConstraint('poll_id', 'user_id', name='uq_poll_user'),
    )

    #ОСНОВНОЕ

    id: Mapped[int] = mapped_column(primary_key=True)

    #ССЫЛКИ

    # В каком опросе
    poll_id: Mapped[int] = mapped_column(
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False
    )

    # Кто проголосовал
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    #ДАННЫЕ ГОЛОСА

    # Индекс выбранного варианта
    option_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Время голосования
    voted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    #СВЯЗИ

    # Опрос
    poll: Mapped["Poll"] = relationship(
        "Poll",
        back_populates="votes"
    )

    # Пользователь
    user: Mapped["User"] = relationship("User")

    #МЕТОДЫ

    def __repr__(self) -> str:
        return f"<PollVote(id={self.id}, poll_id={self.poll_id}, user_id={self.user_id}, option={self.option_index})>"

    def to_dict(self) -> dict:
        """Преобразует объект в словарь."""
        return {
            "id": self.id,
            "poll_id": self.poll_id,
            "user_id": self.user_id,
            "option_index": self.option_index,
            "voted_at": self.voted_at.isoformat() if self.voted_at else None,
            "option_text": self.poll.options[self.option_index] if self.poll else None
        }