from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from repositories.user_repository import UserRepository
from models.user import User, UserRole


class UserService:

    def __init__(self, user_repository: UserRepository | None = None):
        if not user_repository:
            self.user_repo = UserRepository()
        else:
            self.user_repo = user_repository

    async def get_by_tg_id(self, tg_id: int):
        """Получить пользовате по td id"""
        return await self.user_repo.get_by_telegram_id(tg_id)

    async def get_by_tg_username(self, tg_username: str):
        return await self.user_repo.get_by_telegram_username(tg_username)

    async def create_user(self, tg_id: int, username: str | None, full_name: str, role: str, tz: str):
        """Создать пользователя."""
        user = User(
            telegram_id=tg_id,
            username=username,
            full_name=full_name,
            role=role,
            timezone=tz
        )
        return await self.user_repo.create(user)

    async def get_all(self):
        """Получить всех пользователей"""
        return await self.user_repo.get_all()

    async def get_all_participants(self):
        """Получить всех участников"""
        return await self.user_repo.get_all_participants()

    async def delete_user(self, tg_id: int):
        """Удалить пользователя"""
        user = await self.get_by_tg_id(tg_id)
        if user:
            await self.user_repo.delete_hard(user.id)

    async def update_user_by_tg_id(self, tg_id: int, **kwargs):
        """Обновить пользователя по tg id."""
        user = await self.get_by_tg_id(tg_id)
        if user:
            await self.user_repo.update(user.id, **kwargs)

    #МЕТОДЫ ДЛЯ АНКЕТ

    async def get_active_profiles(self, exclude_user_id: Optional[int] = None) -> List[User]:
        """Возвращает активные анкеты участников."""
        return await self.user_repo.get_active_profiles(exclude_user_id)
    
    async def get_random_active_profiles(self, limit: int = 5, exclude_user_id: Optional[int] = None) -> List[User]:
        """Возвращает случайные активные анкеты."""
        return await self.user_repo.get_random_active_profiles(limit, exclude_user_id)
    
    async def update_user_profile(self, user_id: int, profile_text: str) -> bool:
        """Обновляет анкету пользователя."""
        return await self.user_repo.update_profile(user_id, profile_text)
    
    async def set_profile_active(self, user_id: int, active: bool) -> bool:
        """Устанавливает активность анкеты."""
        return await self.user_repo.set_profile_active(user_id, active)
    
    async def get_user_profile_status(self, user_id: int) -> dict:
        """Возвращает статус анкеты пользователя."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {"error": "Пользователь не найден"}
        
        return {
            "has_profile": not user.is_profile_empty(),
            "is_active": user.profile_active,
            "profile_text": user.profile_text or "",
            "has_team": user.team_id is not None,
            "can_activate": user.can_activate_profile() if hasattr(user, 'can_activate_profile') else (not user.team_id and not user.is_profile_empty())
        }