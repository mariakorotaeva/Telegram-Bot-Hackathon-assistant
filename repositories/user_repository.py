# repositories/user_repository.py
"""
Репозиторий для работы с пользователями (Data Access Layer).
Содержит низкоуровневые операции с БД.
"""

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from models.user import User, UserRole, ParticipantStatus


class UserRepository:
    """Репозиторий для работы с таблицей users."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        """Создаёт нового пользователя."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Находит пользователя по ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Находит пользователя по Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, user_id: int, **kwargs) -> bool:
        """Обновляет данные пользователя."""
        stmt = update(User).where(User.id == user_id).values(**kwargs)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def delete(self, user_id: int) -> bool:
        """Удаляет пользователя (мягкое удаление)."""
        stmt = update(User).where(User.id == user_id).values(is_active=False)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_all_participants(self) -> List[User]:
        """Возвращает всех участников."""
        stmt = select(User).where(
            User.role == UserRole.PARTICIPANT,
            User.is_active == True
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_users_looking_for_team(self) -> List[User]:
        """Возвращает участников, ищущих команду."""
        stmt = select(User).where(
            User.role == UserRole.PARTICIPANT,
            User.participant_status == ParticipantStatus.LOOKING_FOR_TEAM,
            User.is_active == True
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_users_by_team(self, team_id: int) -> List[User]:
        """Возвращает всех участников команды."""
        stmt = select(User).where(
            User.team_id == team_id,
            User.is_active == True
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_skills(self, user_id: int, skills: List[str]) -> bool:
        """Обновляет навыки пользователя."""
        return await self.update(user_id, skills=skills)

    async def update_interests(self, user_id: int, interests: List[str]) -> bool:
        """Обновляет интересы пользователя."""
        return await self.update(user_id, interests=interests)

    async def join_team(self, user_id: int, team_id: int) -> bool:
        """Добавляет пользователя в команду."""
        return await self.update(
            user_id,
            team_id=team_id,
            participant_status=ParticipantStatus.IN_TEAM
        )

    async def leave_team(self, user_id: int) -> bool:
        """Удаляет пользователя из команды."""
        return await self.update(
            user_id,
            team_id=None,
            participant_status=ParticipantStatus.LOOKING_FOR_TEAM
        )