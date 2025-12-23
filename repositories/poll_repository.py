# repositories/poll_repository.py
"""
Репозиторий для работы с опросами.
"""

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from models.poll import Poll, PollMessage
from models.poll_vote import PollVote
from config.database import get_db


class PollRepository:
    """Репозиторий для работы с таблицей polls."""

    def __init__(self):
        ...

    # ==================== CRUD ОПЕРАЦИИ ====================

    async def create(self, poll: Poll) -> Poll:
        """Создаёт новый опрос."""
        # Генерируем уникальный ID для опроса
        if not poll.poll_id:
            poll.poll_id = f"poll_{uuid.uuid4().hex[:8]}"

        async with get_db() as session:
            session.add(poll)
            await session.commit()
            await session.refresh(poll)
            return poll

    async def create_poll_message(self, poll: Poll, user: User, poll_tg_id: str) -> PollMessage:
        """Создаёт новый опрос."""
        async with get_db() as session:
            pm = PollMessage(poll_id=poll.id, user_id=user.id, poll_tg_id=poll_tg_id)
            session.add(pm)
            await session.commit()
            await session.refresh(pm)
            return poll

    async def get_by_id(self, poll_id: int) -> Optional[Poll]:
        """Находит опрос по ID."""
        stmt = select(Poll).where(Poll.id == poll_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_poll_id(self, poll_uid: str) -> Optional[Poll]:
        """Находит опрос по poll_id (уникальный строковый ID)."""
        stmt = select(Poll).where(Poll.poll_id == poll_uid)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update(self, poll_id: int, **kwargs) -> bool:
        """Обновляет данные опроса."""
        stmt = update(Poll).where(Poll.id == poll_id).values(**kwargs)
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def delete(self, poll_id: int) -> bool:
        """Удаляет опрос."""
        stmt = delete(Poll).where(Poll.id == poll_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def deactivate(self, poll_id: int) -> bool:
        """Деактивирует опрос."""
        return await self.update(poll_id, is_active=False)

    # ==================== ПОИСК И ФИЛЬТРАЦИЯ ====================

    async def get_all_active(self) -> List[Poll]:
        """Возвращает все активные опросы."""
        stmt = select(Poll).where(
            Poll.is_active == True
        ).order_by(Poll.created_at.desc())
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_by_creator(self, creator_id: int) -> List[Poll]:
        """Возвращает опросы создателя."""
        stmt = select(Poll).where(
            Poll.creator_id == creator_id
        ).order_by(Poll.created_at.desc())
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_expired_polls(self) -> List[Poll]:
        """Возвращает опросы с истекшим сроком."""
        stmt = select(Poll).where(
            Poll.expires_at < datetime.utcnow(),
            Poll.is_active == True
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_by_category(self, category: str) -> List[Poll]:
        """Возвращает опросы по категории."""
        stmt = select(Poll).where(
            Poll.category == category,
            Poll.is_active == True
        ).order_by(Poll.created_at.desc())
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def search_polls(self, search_term: str) -> List[Poll]:
        """Ищет опросы по тексту вопроса."""
        stmt = select(Poll).where(
            Poll.question.ilike(f"%{search_term}%"),
            Poll.is_active == True
        ).order_by(Poll.created_at.desc())
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    # ==================== СТАТИСТИКА ====================

    async def get_total_polls_count(self) -> int:
        """Возвращает общее количество опросов."""
        stmt = select(func.count(Poll.id))
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one()

    async def get_active_polls_count(self) -> int:
        """Возвращает количество активных опросов."""
        stmt = select(func.count(Poll.id)).where(Poll.is_active == True)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one()

    async def get_total_votes_count(self) -> int:
        """Возвращает общее количество голосов во всех опросах."""
        stmt = select(func.sum(Poll.total_votes))
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one() or 0

    async def get_polls_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Возвращает статистику опросов за последние N дней."""
        since_date = datetime.utcnow() - timedelta(days=days)

        # Количество созданных опросов
        stmt_created = select(func.count(Poll.id)).where(Poll.created_at >= since_date)
        async with get_db() as session:
            created_count = await session.execute(stmt_created)

        # Количество голосов
        stmt_votes = select(func.sum(Poll.total_votes)).where(Poll.created_at >= since_date)
        async with get_db() as session:
            votes_count = await session.execute(stmt_votes)

        # Самый популярный опрос
        stmt_popular = select(Poll).where(
            Poll.created_at >= since_date
        ).order_by(Poll.total_votes.desc()).limit(1)
        async with get_db() as session:
            popular_poll = await session.execute(stmt_popular)

        return {
            "created_count": created_count.scalar_one() or 0,
            "votes_count": votes_count.scalar_one() or 0,
            "popular_poll": popular_poll.scalar_one_or_none()
        }