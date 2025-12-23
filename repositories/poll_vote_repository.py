# repositories/poll_vote_repository.py
"""
Репозиторий для работы с голосами в опросах.
"""

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any

from models.poll_vote import PollVote
from models.poll import Poll

from config.database import get_db


class PollVoteRepository:
    """Репозиторий для работы с таблицей poll_votes."""

    def __init__(self):
        ...

    # ==================== CRUD ОПЕРАЦИИ ====================

    async def create(self, vote: PollVote) -> PollVote:
        """Создаёт новый голос."""
        async with get_db() as session:
            session.add(vote)
            await session.commit()
            await session.refresh(vote)
            return vote

    async def get_by_id(self, vote_id: int) -> Optional[PollVote]:
        """Находит голос по ID."""
        stmt = select(PollVote).where(PollVote.id == vote_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update(self, vote_id: int, **kwargs) -> bool:
        """Обновляет данные голоса."""
        stmt = update(PollVote).where(PollVote.id == vote_id).values(**kwargs)
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def delete(self, vote_id: int) -> bool:
        """Удаляет голос."""
        stmt = delete(PollVote).where(PollVote.id == vote_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    # ==================== ПОИСК ГОЛОСОВ ====================

    async def get_vote_by_user_and_poll(self, user_id: int, poll_id: int) -> Optional[PollVote]:
        """Находит голос пользователя в конкретном опросе."""
        stmt = select(PollVote).where(
            PollVote.user_id == user_id,
            PollVote.poll_id == poll_id
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_votes_by_poll(self, poll_id: int) -> List[PollVote]:
        """Возвращает все голоса в опросе."""
        stmt = select(PollVote).where(PollVote.poll_id == poll_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_votes_by_user(self, user_id: int) -> List[PollVote]:
        """Возвращает все голоса пользователя."""
        stmt = select(PollVote).where(PollVote.user_id == user_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_votes_count_by_poll(self, poll_id: int) -> int:
        """Возвращает количество голосов в опросе."""
        stmt = select(func.count(PollVote.id)).where(PollVote.poll_id == poll_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one()

    async def get_voters_by_poll(self, poll_id: int) -> List[int]:
        """Возвращает ID пользователей, проголосовавших в опросе."""
        stmt = select(PollVote.user_id).where(PollVote.poll_id == poll_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return [row[0] for row in result.fetchall()]

    # ==================== РЕЗУЛЬТАТЫ ОПРОСА ====================

    async def get_poll_results(self, poll_id: int) -> Dict[int, int]:
        """Возвращает результаты опроса в формате {индекс_варианта: количество_голосов}."""
        stmt = select(
            PollVote.option_index,
            func.count(PollVote.id).label('count')
        ).where(
            PollVote.poll_id == poll_id
        ).group_by(
            PollVote.option_index
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            rows = result.fetchall()

        # Создаём словарь с результатами
        results_dict = {}
        for row in rows:
            results_dict[row[0]] = row[1]

        return results_dict

    async def get_detailed_results(self, poll_id: int) -> List[Dict[str, Any]]:
        """Возвращает детализированные результаты опроса."""
        # Этот запрос более сложный, можно оптимизировать при необходимости
        stmt = select(
            PollVote.option_index,
            func.count(PollVote.id).label('vote_count'),
            func.array_agg(PollVote.user_id).label('voter_ids')
        ).where(
            PollVote.poll_id == poll_id
        ).group_by(
            PollVote.option_index
        )

        async with get_db() as session:
            result = await session.execute(stmt)
            rows = result.fetchall()

        detailed_results = []
        for row in rows:
            detailed_results.append({
                "option_index": row[0],
                "vote_count": row[1],
                "voter_ids": row[2] if row[2] else []
            })

        return detailed_results

    # ==================== ПРОВЕРКИ ====================

    async def has_user_voted(self, user_id: int, poll_id: int) -> bool:
        """Проверяет, голосовал ли пользователь в опросе."""
        stmt = select(func.count(PollVote.id)).where(
            PollVote.user_id == user_id,
            PollVote.poll_id == poll_id
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one() > 0

    async def get_user_vote_details(self, user_id: int, poll_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает детали голоса пользователя."""
        vote = await self.get_vote_by_user_and_poll(user_id, poll_id)

        if not vote:
            return None

        # Получаем информацию об опросе
        stmt = select(Poll).where(Poll.id == poll_id)
        async with get_db() as session:
            poll_result = await session.execute(stmt)
            poll = poll_result.scalar_one_or_none()

            if not poll:
                return None

        return {
            "vote_id": vote.id,
            "poll_id": poll_id,
            "poll_question": poll.question,
            "user_id": user_id,
            "option_index": vote.option_index,
            "option_text": poll.options[vote.option_index] if vote.option_index < len(poll.options) else None,
            "voted_at": vote.voted_at.isoformat() if vote.voted_at else None
        }