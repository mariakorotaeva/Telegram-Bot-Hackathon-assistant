from sqlalchemy import select, update, delete, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Tuple

from models.team import Team
from models.user import User
from config.database import get_db


class TeamRepository:
    
    def __init__(self): ...
    
    async def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """Находит команду по ID."""
        stmt = select(Team).where(Team.id == team_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_team_by_name(self, name: str) -> Optional[Team]:
        """Находит команду по названию."""
        stmt = select(Team).where(Team.name == name)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_team_by_captain(self, captain_id: int) -> Optional[Team]:
        """Находит команду по ID капитана."""
        stmt = select(Team).where(Team.captain_id == captain_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_user_team(self, user_id: int) -> Optional[Team]:
        """Находит команду пользователя."""
        stmt = select(Team).join(User).where(User.id == user_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def create_team(self, captain_id: int, name: str) -> Team:
        """Создаёт новую команду."""
        team = Team(
            name=name,
            captain_id=captain_id
        )
        
        async with get_db() as session:
            captain_stmt = select(User).where(User.id == captain_id)
            captain_result = await session.execute(captain_stmt)
            captain = captain_result.scalar_one()
            
            session.add(team)
            await session.flush()
            
            captain.team_id = team.id
            
            await session.commit()
            await session.refresh(team)
            return team
    
    async def update_team_name(self, team_id: int, name: str) -> Optional[Team]:
        """Обновляет название команды."""
        stmt = update(Team).where(Team.id == team_id).values(name=name)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                return await self.get_team_by_id(team_id)
            return None
    
    async def assign_mentor(self, team_id: int, mentor_id: int) -> Optional[Team]:
        """Назначает ментора команде."""
        stmt = update(Team).where(Team.id == team_id).values(mentor_id=mentor_id)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                return await self.get_team_by_id(team_id)
            return None
    
    async def remove_mentor(self, team_id: int) -> Optional[Team]:
        """Удаляет ментора из команды."""
        stmt = update(Team).where(Team.id == team_id).values(mentor_id=None)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                return await self.get_team_by_id(team_id)
            return None
    
    async def delete_team(self, team_id: int) -> bool:
        """Удаляет команду."""
        stmt = delete(Team).where(Team.id == team_id)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    async def get_all_teams(self) -> List[Team]:
        """Возвращает все команды."""
        stmt = select(Team)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_teams_without_mentor(self) -> List[Team]:
        """Возвращает команды без ментора."""
        stmt = select(Team).where(Team.mentor_id == None)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def is_user_in_team(self, user_id: int) -> bool:
        """Проверяет, состоит ли пользователь в команде."""
        stmt = select(User).where(User.id == user_id, User.team_id != None)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
    
    async def is_user_captain(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь капитаном."""
        stmt = select(Team).where(Team.captain_id == user_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None
    
    async def get_team_members(self, team_id: int) -> List[User]:
        """Возвращает участников команды."""
        stmt = select(User).where(User.team_id == team_id)
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def remove_user_from_team(self, user_id: int) -> bool:
        """Удаляет пользователя из команды."""
        stmt = update(User).where(User.id == user_id).values(team_id=None)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    async def get_available_participants(self, exclude_team_id: Optional[int] = None) -> List[User]:
        """Возвращает участников без команды."""
        from models.user import UserRole
        
        stmt = select(User).where(
            and_(
                User.role == UserRole.PARTICIPANT,
                User.team_id == None
            )
        )
        
        if exclude_team_id:
            stmt = stmt.where(User.team_id != exclude_team_id)
        
        async with get_db() as session:
            result = await session.execute(stmt)
            return result.scalars().all()