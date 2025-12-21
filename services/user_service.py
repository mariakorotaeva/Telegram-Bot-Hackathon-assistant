# services/user_service.py
"""
Сервисный слой для работы с пользователями.
Бизнес-логика для пользователей.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from repositories.user_repository import UserRepository
from models.user import User, UserRole


class UserService:
    """Сервис для работы с пользователями."""

    def __init__(self, user_repository: UserRepository | None = None):
        if not user_repository:
            self.user_repo = UserRepository()
        else:
            self.user_repo = user_repository

    async def get_by_tg_id(self, tg_id: int):
        return await self.user_repo.get_by_telegram_id(tg_id)

    async def create_user(self, tg_id: int, username: str | None, full_name: str, role: str, tz: str):
        user = User(
            telegram_id=tg_id,
            username=username,
            full_name=full_name,
            role=role,
            timezone=tz
        )
        return await self.user_repo.create(user)

    async def get_all(self):
        return await self.user_repo.get_all()

    async def get_all_participants(self):
        return await self.user_repo.get_all_participants()

    async def delete_user(self, tg_id: int):
        user = await self.get_by_tg_id(tg_id)
        if user:
            await self.user_repo.delete_hard(user.id)

    async def update_user_by_tg_id(self, tg_id: int, **kwargs):
        user = await self.get_by_tg_id(tg_id)
        if user:
            await self.user_repo.update(user.id, **kwargs)