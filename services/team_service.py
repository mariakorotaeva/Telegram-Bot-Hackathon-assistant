"""
Сервис для работы с командами и приглашениями.
"""
from typing import Optional, List, Tuple
from datetime import datetime

from repositories.team_repository import TeamRepository
from repositories.user_repository import UserRepository
from models.team import Team, TeamInvitation, InvitationStatus
from models.user import User, UserRole


class TeamService:
    """Сервис для работы с командами."""
    
    def __init__(self, team_repo: Optional[TeamRepository] = None, user_repo: Optional[UserRepository] = None):
        self.team_repo = team_repo or TeamRepository()
        self.user_repo = user_repo or UserRepository()
    
    # ==================== ОСНОВНЫЕ МЕТОДЫ КОМАНД ====================
    
    async def create_team(self, captain_id: int, name: str) -> Tuple[bool, Optional[Team], str]:
        """
        Создаёт новую команду.
        
        Returns:
            Tuple[success: bool, team: Optional[Team], message: str]
        """
        # Проверяем, что пользователь существует и является участником
        user = await self.user_repo.get_by_id(captain_id)
        if not user:
            return False, None, "Пользователь не найден"
        
        if user.role != UserRole.PARTICIPANT:
            return False, None, "Только участники могут создавать команды"
        
        # Проверяем, что пользователь не состоит в команде
        if await self.team_repo.is_user_in_team(captain_id):
            return False, None, "Вы уже состоите в команде"
        
        # Проверяем, что пользователь не является капитаном другой команды
        if await self.team_repo.is_user_captain(captain_id):
            return False, None, "Вы уже являетесь капитаном команды"
        
        # Проверяем, что название команды свободно
        existing_team = await self.team_repo.get_team_by_name(name)
        if existing_team:
            return False, None, "Команда с таким названием уже существует"
        
        # Создаём команду
        try:
            team = await self.team_repo.create_team(captain_id, name)
            return True, team, f"Команда '{name}' создана!"
        except Exception as e:
            return False, None, f"Ошибка при создании команды: {str(e)}"
    
    async def get_user_team(self, user_id: int) -> Optional[Team]:
        """Возвращает команду пользователя."""
        return await self.team_repo.get_user_team(user_id)
    
    async def update_team_name(self, user_id: int, new_name: str) -> Tuple[bool, Optional[Team], str]:
        """Обновляет название команды (только для капитана)."""
        team = await self.team_repo.get_team_by_captain(user_id)
        
        if not team:
            return False, None, "Вы не являетесь капитаном команды"
        
        # Проверяем, что название свободно
        existing_team = await self.team_repo.get_team_by_name(new_name)
        if existing_team and existing_team.id != team.id:
            return False, None, "Команда с таким названием уже существует"
        
        updated_team = await self.team_repo.update_team_name(team.id, new_name)
        if updated_team:
            return True, updated_team, f"Название команды изменено на '{new_name}'"
        return False, None, "Ошибка при изменении названия"
    
    async def assign_mentor(self, team_id: int, mentor_id: int) -> Tuple[bool, Optional[Team], str]:
        """Назначает ментора команде (только для организаторов)."""
        # Проверяем, что ментор существует и является ментором или организатором
        mentor = await self.user_repo.get_by_id(mentor_id)
        if not mentor:
            return False, None, "Ментор не найден"
        
        if mentor.role not in [UserRole.MENTOR, UserRole.ORGANIZER]:
            return False, None, "Только менторы или организаторы могут быть назначены менторами команд"
        
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
    
    # ==================== МЕТОДЫ ДЛЯ ПРИГЛАШЕНИЙ ====================
    
    async def invite_to_team(self, captain_id: int, invited_user_id: int) -> Tuple[bool, Optional[TeamInvitation], str]:
        """
        Отправляет приглашение в команду.
        
        Returns:
            Tuple[success: bool, invitation: Optional[TeamInvitation], message: str]
        """
        # Проверяем, что капитан является капитаном команды
        team = await self.team_repo.get_team_by_captain(captain_id)
        if not team:
            return False, None, "Вы не являетесь капитаном команды"
        
        # Проверяем, что команда не полная
        if team.is_full:
            return False, None, "Команда уже полная (максимум 5 человек)"
        
        # Проверяем, что приглашаемый пользователь существует
        invited_user = await self.user_repo.get_by_id(invited_user_id)
        if not invited_user:
            return False, None, "Пользователь не найден"
        
        if invited_user.role != UserRole.PARTICIPANT:
            return False, None, "Можно приглашать только участников"
        
        # Проверяем, что пользователь не в команде
        if invited_user.team_id:
            return False, None, "Пользователь уже состоит в команде"
        
        # Проверяем, что пользователь не капитан
        if invited_user.id == captain_id:
            return False, None, "Вы не можете пригласить себя"
        
        # Проверяем, нет ли уже активного приглашения
        if await self.team_repo.has_pending_invitation(team.id, invited_user_id):
            return False, None, "У пользователя уже есть активное приглашение"
        
        # Создаём приглашение
        try:
            invitation = await self.team_repo.create_invitation(
                team_id=team.id,
                user_id=invited_user_id,
                invited_by_id=captain_id
            )
            return True, invitation, f"Приглашение отправлено {invited_user.full_name}"
        except Exception as e:
            return False, None, f"Ошибка при отправке приглашения: {str(e)}"
    
    async def get_user_invitations(self, user_id: int) -> List[TeamInvitation]:
        """Возвращает активные приглашения пользователя."""
        return await self.team_repo.get_pending_invitations_for_user(user_id)
    
    async def accept_invitation(self, invitation_id: int, user_id: int) -> Tuple[bool, Optional[Team], str]:
        """Принимает приглашение."""
        invitation = await self.team_repo.get_invitation_by_id(invitation_id)
        
        if not invitation:
            return False, None, "Приглашение не найдено"
        
        if invitation.user_id != user_id:
            return False, None, "Это не ваше приглашение"
        
        if invitation.status != InvitationStatus.PENDING:
            return False, None, "Приглашение уже обработано"
        
        if invitation.is_expired():
            return False, None, "Срок действия приглашения истёк"
        
        success, team = await self.team_repo.accept_invitation(invitation_id)
        if success and team:
            return True, team, f"Вы присоединились к команде '{team.name}'!"
        return False, None, "Не удалось присоединиться к команде"
    
    async def reject_invitation(self, invitation_id: int, user_id: int) -> Tuple[bool, str]:
        """Отклоняет приглашение."""
        invitation = await self.team_repo.get_invitation_by_id(invitation_id)
        
        if not invitation:
            return False, "Приглашение не найдено"
        
        if invitation.user_id != user_id:
            return False, "Это не ваше приглашение"
        
        if invitation.status != InvitationStatus.PENDING:
            return False, "Приглашение уже обработано"
        
        success = await self.team_repo.reject_invitation(invitation_id)
        if success:
            return True, "Приглашение отклонено"
        return False, "Не удалось отклонить приглашение"
    
    async def cancel_invitation(self, invitation_id: int, captain_id: int) -> Tuple[bool, str]:
        """Отменяет приглашение (только капитан)."""
        invitation = await self.team_repo.get_invitation_by_id(invitation_id)
        
        if not invitation:
            return False, "Приглашение не найдено"
        
        # Проверяем, что отменяет капитан команды
        team = await self.team_repo.get_team_by_captain(captain_id)
        if not team or team.id != invitation.team_id:
            return False, "Только капитан команды может отменить приглашение"
        
        success = await self.team_repo.cancel_invitation(invitation_id)
        if success:
            return True, "Приглашение отменено"
        return False, "Не удалось отменить приглашение"
    
    async def get_team_invitations(self, captain_id: int) -> List[TeamInvitation]:
        """Возвращает приглашения команды (только для капитана)."""
        team = await self.team_repo.get_team_by_captain(captain_id)
        if not team:
            return []
        
        return await self.team_repo.get_pending_invitations_for_team(team.id)
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    async def leave_team(self, user_id: int) -> Tuple[bool, str]:
        """Покидает команду."""
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.team_id:
            return False, "Вы не состоите в команде"
        
        team = await self.team_repo.get_team_by_id(user.team_id)
        if not team:
            return False, "Команда не найдена"
        
        # Капитан не может покинуть команду
        if team.captain_id == user_id:
            return False, "Капитан не может покинуть команду. Распустите команду или передайте капитанство"
        
        success = await self.team_repo.remove_user_from_team(user_id)
        if success:
            return True, f"Вы покинули команду '{team.name}'"
        return False, "Не удалось покинуть команду"
    
    async def dissolve_team(self, captain_id: int) -> Tuple[bool, str]:
        """Распускает команду (только капитан)."""
        team = await self.team_repo.get_team_by_captain(captain_id)
        if not team:
            return False, "Вы не являетесь капитаном команды"
        
        success = await self.team_repo.delete_team(team.id)
        if success:
            return True, f"Команда '{team.name}' распущена"
        return False, "Не удалось распустить команду"
    
    async def get_available_participants(self, captain_id: int) -> List[User]:
        """Возвращает участников без команды для приглашения."""
        team = await self.team_repo.get_team_by_captain(captain_id)
        if not team:
            return []
        
        return await self.team_repo.get_available_participants(exclude_team_id=team.id)
    
    async def is_user_captain(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь капитаном."""
        return await self.team_repo.is_user_captain(user_id)
    
    async def is_user_in_team(self, user_id: int) -> bool:
        """Проверяет, состоит ли пользователь в команде."""
        return await self.team_repo.is_user_in_team(user_id)