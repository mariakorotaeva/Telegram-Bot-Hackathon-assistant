from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from models.user import User, UserRole, ParticipantStatus
from config.database import get_db


class UserRepository:

    def __init__(self): ...

    async def create(self, user: User) -> User:
        """Создаёт нового пользователя."""
        async with get_db() as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Находит пользователя по ID."""
        stmt = select(User).where(User.id == user_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Находит пользователя по Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update(self, user_id: int, **kwargs) -> bool:
        """Обновляет данные пользователя."""
        stmt = update(User).where(User.id == user_id).values(**kwargs)
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def delete_soft(self, user_id: int) -> bool:
        """Удаляет пользователя (мягкое удаление)."""
        stmt = update(User).where(User.id == user_id).values(is_active=False)
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def delete_hard(self, user_id: int) -> bool:
        """Удаляет пользователя (жесткое удаление)."""
        stmt = delete(User).where(User.id == user_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    async def get_all(self) -> List[User]:
        """Возвращает всех пользователей."""
        stmt = select(User).where(User.is_active == True)  # Только активных
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_all_participants(self) -> List[User]:
        """Возвращает всех участников."""
        stmt = select(User).where(
            User.role == UserRole.PARTICIPANT,
            User.is_active == True
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_users_looking_for_team(self) -> List[User]:
        """Возвращает участников, ищущих команду."""
        stmt = select(User).where(
            User.role == UserRole.PARTICIPANT,
            User.participant_status == ParticipantStatus.LOOKING_FOR_TEAM,
            User.is_active == True
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_users_by_team(self, team_id: int) -> List[User]:
        """Возвращает всех участников команды."""
        stmt = select(User).where(
            User.team_id == team_id,
            User.is_active == True
        )
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()

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

    async def update_profile(self, user_id: int, profile_text: str) -> bool:
        """Обновляет анкету пользователя."""
        return await self.update(
            user_id, 
            profile_text=profile_text,
        )
    
    async def set_profile_active(self, user_id: int, active: bool) -> bool:
        """Устанавливает активность анкеты."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        if active and user.team_id:
            return False
        
        if active and (not user.profile_text or not user.profile_text.strip()):
            return False
        
        return await self.update(
            user_id, 
            profile_active=active,
        )
    
    async def get_active_profiles(self, exclude_user_id: Optional[int] = None) -> List[User]:
        """Возвращает активные анкеты участников."""
        stmt = select(User).where(
            User.role == UserRole.PARTICIPANT,
            User.profile_active == True,
            User.is_active == True,
            User.team_id == None
        )
        
        if exclude_user_id:
            stmt = stmt.where(User.id != exclude_user_id)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_random_active_profiles(self, limit: int = 5, exclude_user_id: Optional[int] = None) -> List[User]:
        """Возвращает случайные активные анкеты."""
        from sqlalchemy import func
        
        stmt = select(User).where(
            User.role == UserRole.PARTICIPANT,
            User.profile_active == True,
            User.is_active == True,
            User.team_id == None
        )
        
        if exclude_user_id:
            stmt = stmt.where(User.id != exclude_user_id)
        
        stmt = stmt.order_by(func.random()).limit(limit)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()