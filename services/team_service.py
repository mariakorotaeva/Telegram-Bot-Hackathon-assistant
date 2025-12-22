from typing import Optional, List, Tuple
from datetime import datetime

from repositories.team_repository import TeamRepository
from repositories.user_repository import UserRepository
from models.team import Team
from models.user import User, UserRole


class TeamService:
    
    def __init__(self, team_repo: Optional[TeamRepository] = None, user_repo: Optional[UserRepository] = None):
        self.team_repo = team_repo or TeamRepository()
        self.user_repo = user_repo or UserRepository()
    
    
    async def create_team(self, captain_id: int, name: str) -> Tuple[bool, Optional[Team], str]:
        """Создаёт новую команду."""
        user = await self.user_repo.get_by_id(captain_id)
        if not user:
            return False, None, "❌Пользователь не найден, для регистрации нажмите /start"
        
        if user.role != UserRole.PARTICIPANT:
            return False, None, "Только участники могут создавать команды"
        
        if await self.team_repo.is_user_in_team(captain_id):
            return False, None, "Вы уже состоите в команде"
        
        if await self.team_repo.is_user_captain(captain_id):
            return False, None, "Вы уже являетесь капитаном команды"
        
        existing_team = await self.team_repo.get_team_by_name(name)
        if existing_team:
            return False, None, "Команда с таким названием уже существует"
        
        try:
            team = await self.team_repo.create_team(captain_id, name)
            return True, team, f"Команда '{name}' создана!"
        except Exception as e:
            return False, None, f"Ошибка при создании команды: {str(e)}"
    
    async def get_user_team(self, user_id: int) -> Optional[Team]:
        """Возвращает команду пользователя."""
        return await self.team_repo.get_user_team(user_id)
    
    async def update_team_name(self, user_id: int, new_name: str) -> Tuple[bool, Optional[Team], str]:
        """Обновляет название команды."""
        team = await self.team_repo.get_team_by_captain(user_id)
        
        if not team:
            return False, None, "Вы не являетесь капитаном команды"
        
        existing_team = await self.team_repo.get_team_by_name(new_name)
        if existing_team and existing_team.id != team.id:
            return False, None, "Команда с таким названием уже существует"
        
        updated_team = await self.team_repo.update_team_name(team.id, new_name)
        if updated_team:
            return True, updated_team, f"Название команды изменено на '{new_name}'"
        return False, None, "Ошибка при изменении названия"
    
    async def assign_mentor(self, team_id: int, mentor_id: int) -> Tuple[bool, Optional[Team], str]:
        """Назначает ментора команде."""
        mentor = await self.user_repo.get_by_id(mentor_id)
        if not mentor:
            return False, None, "Ментор не найден"
        
        if mentor.role not in [UserRole.MENTOR]:
            return False, None, "Только менторы могут быть назначены менторами команд"
        
        team = await self.team_repo.get_team_by_id(team_id)
        if not team:
            return False, None, "Команда не найдена"
        
        if team.mentor_id:
            return False, None, "У команды уже есть ментор"
        
        updated_team = await self.team_repo.assign_mentor(team_id, mentor_id)
        if updated_team:
            return True, updated_team, f"Ментор {mentor.full_name} назначен команде '{team.name}'"
        return False, None, "Ошибка при назначении ментора"
    
    async def get_team_info(self, team_id: int) -> Optional[Team]:
        """Возвращает полную информацию о команде."""
        return await self.team_repo.get_team_by_id(team_id)
    
    async def get_all_teams(self) -> List[Team]:
        """Возвращает все команды."""
        return await self.team_repo.get_all_teams()
    
    async def get_teams_without_mentor(self) -> List[Team]:
        """Возвращает команды без ментора."""
        return await self.team_repo.get_teams_without_mentor()
    
    async def leave_team(self, user_id: int) -> Tuple[bool, str]:
        """Покидает команду."""
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.team_id:
            return False, "Вы не состоите в команде"
        
        team = await self.team_repo.get_team_by_id(user.team_id)
        if not team:
            return False, "Команда не найдена"
        
        if team.captain_id == user_id:
            return False, "Капитан не может покинуть команду. Распустите команду или передайте капитанство"
        
        success = await self.team_repo.remove_user_from_team(user_id)
        if success:
            return True, f"Вы покинули команду '{team.name}'"
        return False, "Не удалось покинуть команду"
    
    async def dissolve_team(self, captain_id: int) -> Tuple[bool, str]:
        """Распускает команду."""
        team = await self.team_repo.get_team_by_captain(captain_id)
        if not team:
            return False, "Вы не являетесь капитаном команды"
        
        success = await self.team_repo.delete_team(team.id)
        if success:
            return True, f"Команда '{team.name}' распущена"
        return False, "Не удалось распустить команду"
    
    async def is_user_captain(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь капитаном."""
        return await self.team_repo.is_user_captain(user_id)
    
    async def is_user_in_team(self, user_id: int) -> bool:
        """Проверяет, состоит ли пользователь в команде."""
        return await self.team_repo.is_user_in_team(user_id)