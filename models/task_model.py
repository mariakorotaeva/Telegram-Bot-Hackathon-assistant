from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from config.database import Base
from datetime import datetime
from typing import List, Optional


class TaskModel(Base):
    
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    assigned_to = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    completed_by = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    
    # def __repr__(self):
    #     return f"Task(id={self.id}, title={self.title}, assigned_to={self.assigned_to})"
    
    # def to_dict(self) -> dict:
    #     """Преобразовать объект задачи в словарь"""
    #     return {
    #         "id": self.id,
    #         "telegram_id": self.telegram_id,
    #         "title": self.title,
    #         "description": self.description,
    #         "assigned_to": self.assigned_to,
    #         "created_by": self.created_by,
    #         "created_at": self.created_at.isoformat() if self.created_at else None,
    #         "completed_by": self.completed_by or [],
    #         "is_active": self.is_active
    #     }


class Task:
    
    def __init__(
        self,
        telegram_id: str,
        title: str,
        description: str,
        assigned_to: str,
        created_by: str,
        completed_by: Optional[List[str]] = None,
        is_active: bool = True
    ):
        self.telegram_id = telegram_id
        self.title = title
        self.description = description
        self.assigned_to = assigned_to
        self.created_by = created_by
        self.completed_by = completed_by or []
        self.is_active = is_active
    
    #ЧТО ЭТО???

    @classmethod
    def from_model(cls, model: TaskModel) -> 'Task':
        return cls(
            telegram_id=model.telegram_id,
            title=model.title,
            description=model.description,
            assigned_to=model.assigned_to,
            created_by=model.created_by,
            created_at=model.created_at,
            completed_by=model.completed_by,
            is_active=model.is_active
        )
    
    # def to_model(self) -> TaskModel:
    #     """Преобразовать в модель БД"""
    #     return TaskModel(
    #         telegram_id=self.telegram_id,
    #         title=self.title,
    #         description=self.description,
    #         assigned_to=self.assigned_to,
    #         created_by=self.created_by,
    #         created_at=self.created_at,
    #         completed_by=self.completed_by,
    #         is_active=self.is_active
    #     )
    
    # def to_dict(self) -> dict:
    #     """Преобразовать в словарь"""
    #     return {
    #         "telegram_id": self.telegram_id,
    #         "title": self.title,
    #         "description": self.description,
    #         "assigned_to": self.assigned_to,
    #         "created_by": self.created_by,
    #         "created_at": self.created_at.isoformat(),
    #         "completed_by": self.completed_by,
    #         "is_active": self.is_active
    #     }
    
    def mark_completed(self, volunteer_id: str) -> bool:
        """Пометить задачу как выполненную волонтером"""
        if volunteer_id not in self.completed_by:
            self.completed_by.append(volunteer_id)
            return True
        return False
    
    def is_completed_by(self, volunteer_id: str) -> bool:
        """Проверить, выполнена ли задача волонтером"""
        return volunteer_id in self.completed_by
    
    def is_assigned_to(self, volunteer_id: str) -> bool:
        """Проверить, назначена ли задача волонтеру"""
        return self.assigned_to == volunteer_id or self.assigned_to == "all"