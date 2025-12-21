from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from models.task_model import Task
from repositories.task_repository import TaskRepository


class TaskService:
    """Сервис для работы с задачами"""
    
    def __init__(self):
        self.task_repo = TaskRepository()
    
    async def create_task(
        self,
        title: str,
        description: str,
        assigned_to: str,
        created_by: str
    ) -> Task:
        """Создать новую задачу"""
        task_telegram_id = f"task_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        
        task = Task(
            telegram_id=task_telegram_id,
            title=title,
            description=description,
            assigned_to=assigned_to,
            created_by=created_by
        )
        
        return await self.task_repo.create(task)
    
    async def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Получить задачу по ID"""
        return await self.task_repo.get_by_id(task_id)
    
    async def get_task_by_telegram_id(self, telegram_id: str) -> Optional[Task]:
        """Получить задачу по telegram_id"""
        return await self.task_repo.get_by_telegram_id(telegram_id)
    
    async def update_task(
        self,
        telegram_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> Optional[Task]:
        """Обновить задачу"""
        task = await self.get_task_by_telegram_id(telegram_id)
        if not task:
            return None
        
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if assigned_to is not None:
            task.assigned_to = assigned_to
        
        return await self.task_repo.update(task)
    
    async def delete_task(self, telegram_id: str) -> bool:
        """Удалить задачу (пометить как неактивную)"""
        return await self.task_repo.delete(telegram_id)
    
    async def get_all_tasks(self, only_active: bool = True) -> List[Task]:
        """Получить все задачи"""
        return await self.task_repo.get_all(only_active=only_active)
    
    async def get_organizer_tasks(self, organizer_id: str) -> List[Task]:
        """Получить задачи организатора"""
        return await self.task_repo.get_by_creator(organizer_id)
    
    async def get_volunteer_tasks(self, volunteer_id: str) -> List[Task]:
        """Получить задачи волонтера"""
        return await self.task_repo.get_by_assignee(volunteer_id)
    
    async def get_volunteer_active_tasks(self, volunteer_id: str) -> List[Task]:
        """Получить активные (невыполненные) задачи волонтера"""
        return await self.task_repo.get_active_by_assignee(volunteer_id)
    
    async def get_volunteer_completed_tasks(self, volunteer_id: str) -> List[Task]:
        """Получить выполненные задачи волонтера"""
        return await self.task_repo.get_completed_by_assignee(volunteer_id)
    
    async def get_tasks_statistics(self, organizer_id: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику по задачам"""
        return await self.task_repo.get_statistics(organizer_id)
    
    async def mark_task_completed(self, task_telegram_id: str, volunteer_id: str) -> bool:
        """Пометить задачу как выполненную волонтером"""
        return await self.task_repo.mark_completed(task_telegram_id, volunteer_id)
    
    async def is_task_assigned_to(self, task_telegram_id: str, volunteer_id: str) -> bool:
        """Проверить, назначена ли задача волонтеру"""
        task = await self.get_task_by_telegram_id(task_telegram_id)
        if not task:
            return False
        
        return task.is_assigned_to(volunteer_id)
    
    async def is_task_completed_by(self, task_telegram_id: str, volunteer_id: str) -> bool:
        """Проверить, выполнена ли задача волонтером"""
        task = await self.get_task_by_telegram_id(task_telegram_id)
        if not task:
            return False
        
        return task.is_completed_by(volunteer_id)
    
    async def get_tasks_for_broadcast(self, volunteer_id: Optional[str] = None) -> List[Task]:
        """Получить задачи для рассылки (фильтрация по назначению)"""
        if volunteer_id:
            return await self.get_volunteer_active_tasks(volunteer_id)
        return await self.get_all_tasks(only_active=True)