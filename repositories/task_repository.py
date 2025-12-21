from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime

from models.task_model import TaskModel, Task
from database import get_db


class TaskRepository:
    """Репозиторий для работы с задачами в БД"""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
    
    async def get_by_id(self, task_id: int) -> Optional[Task]:
        """Получить задачу по ID"""
        async with get_db() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(stmt)
            task_model = result.scalar_one_or_none()
            
            if task_model:
                return Task.from_model(task_model)
            return None
    
    async def get_by_telegram_id(self, telegram_id: str) -> Optional[Task]:
        """Получить задачу по telegram_id"""
        async with get_db() as session:
            stmt = select(TaskModel).where(TaskModel.telegram_id == telegram_id)
            result = await session.execute(stmt)
            task_model = result.scalar_one_or_none()
            
            if task_model:
                return Task.from_model(task_model)
            return None
    
    async def create(self, task: Task) -> Task:
        """Создать новую задачу"""
        async with get_db() as session:
            task_model = task.to_model()
            session.add(task_model)
            await session.commit()
            await session.refresh(task_model)
            return Task.from_model(task_model)
    
    async def update(self, task: Task) -> Task:
        """Обновить задачу"""
        async with get_db() as session:
            stmt = (
                update(TaskModel)
                .where(TaskModel.telegram_id == task.telegram_id)
                .values(
                    title=task.title,
                    description=task.description,
                    assigned_to=task.assigned_to,
                    completed_by=task.completed_by,
                    is_active=task.is_active
                )
            )
            await session.execute(stmt)
            await session.commit()
            return task
    
    async def delete(self, telegram_id: str) -> bool:
        """Удалить задачу (пометить как неактивную)"""
        async with get_db() as session:
            stmt = (
                update(TaskModel)
                .where(TaskModel.telegram_id == telegram_id)
                .values(is_active=False)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    async def get_all(self, only_active: bool = True) -> List[Task]:
        """Получить все задачи"""
        async with get_db() as session:
            stmt = select(TaskModel)
            if only_active:
                stmt = stmt.where(TaskModel.is_active == True)
            stmt = stmt.order_by(TaskModel.created_at.desc())
            
            result = await session.execute(stmt)
            task_models = result.scalars().all()
            
            return [Task.from_model(model) for model in task_models]
    
    async def get_by_creator(self, creator_id: str, only_active: bool = True) -> List[Task]:
        """Получить задачи по создателю"""
        async with get_db() as session:
            stmt = select(TaskModel).where(TaskModel.created_by == creator_id)
            if only_active:
                stmt = stmt.where(TaskModel.is_active == True)
            stmt = stmt.order_by(TaskModel.created_at.desc())
            
            result = await session.execute(stmt)
            task_models = result.scalars().all()
            
            return [Task.from_model(model) for model in task_models]
    
    async def get_by_assignee(self, assignee_id: str, only_active: bool = True) -> List[Task]:
        """Получить задачи по исполнителю"""
        async with get_db() as session:
            stmt = select(TaskModel).where(
                (TaskModel.assigned_to == assignee_id) | (TaskModel.assigned_to == "all")
            )
            if only_active:
                stmt = stmt.where(TaskModel.is_active == True)
            stmt = stmt.order_by(TaskModel.created_at.desc())
            
            result = await session.execute(stmt)
            task_models = result.scalars().all()
            
            return [Task.from_model(model) for model in task_models]
    
    async def get_active_by_assignee(self, assignee_id: str) -> List[Task]:
        """Получить активные (невыполненные) задачи по исполнителю"""
        async with get_db() as session:
            stmt = select(TaskModel).where(
                ((TaskModel.assigned_to == assignee_id) | (TaskModel.assigned_to == "all")) &
                (TaskModel.is_active == True)
            ).order_by(TaskModel.created_at.desc())
            
            result = await session.execute(stmt)
            task_models = result.scalars().all()
            
            # Фильтруем выполненные задачи
            tasks = [Task.from_model(model) for model in task_models]
            return [task for task in tasks if assignee_id not in task.completed_by]
    
    async def get_completed_by_assignee(self, assignee_id: str) -> List[Task]:
        """Получить выполненные задачи по исполнителю"""
        async with get_db() as session:
            stmt = select(TaskModel).where(
                ((TaskModel.assigned_to == assignee_id) | (TaskModel.assigned_to == "all")) &
                (TaskModel.is_active == True)
            ).order_by(TaskModel.created_at.desc())
            
            result = await session.execute(stmt)
            task_models = result.scalars().all()
            
            # Фильтруем только выполненные задачи
            tasks = [Task.from_model(model) for model in task_models]
            return [task for task in tasks if assignee_id in task.completed_by]
    
    async def get_statistics(self, creator_id: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику по задачам"""
        async with get_db() as session:
            stmt = select(TaskModel).where(TaskModel.is_active == True)
            if creator_id:
                stmt = stmt.where(TaskModel.created_by == creator_id)
            
            result = await session.execute(stmt)
            all_tasks = [Task.from_model(model) for model in result.scalars().all()]
            
            total_tasks = len(all_tasks)
            completed_tasks = sum(1 for task in all_tasks if task.completed_by)
            personal_tasks = [task for task in all_tasks if task.assigned_to != "all"]
            group_tasks = [task for task in all_tasks if task.assigned_to == "all"]
            
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "not_completed_tasks": total_tasks - completed_tasks,
                "personal_tasks": len(personal_tasks),
                "group_tasks": len(group_tasks),
                "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0
            }
    
    async def mark_completed(self, task_telegram_id: str, volunteer_id: str) -> bool:
        """Пометить задачу как выполненную волонтером"""
        async with get_db() as session:
            stmt = select(TaskModel).where(TaskModel.telegram_id == task_telegram_id)
            result = await session.execute(stmt)
            task_model = result.scalar_one_or_none()
            
            if not task_model:
                return False
            
            # Получаем текущий список выполнивших
            completed_by = task_model.completed_by or []
            if volunteer_id not in completed_by:
                completed_by.append(volunteer_id)
                
                update_stmt = (
                    update(TaskModel)
                    .where(TaskModel.telegram_id == task_telegram_id)
                    .values(completed_by=completed_by)
                )
                await session.execute(update_stmt)
                await session.commit()
                return True
            
            return False