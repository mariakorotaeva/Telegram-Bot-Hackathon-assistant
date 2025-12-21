"""
Модель для хранения настроек уведомлений пользователей.
"""
from sqlalchemy import Boolean, ARRAY, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List, Dict, Any
import json

from config.database import Base


class NotificationSettings(Base):
    
    __tablename__ = "notification_settings"
    
    # Первичный ключ
    user_id: Mapped[int] = mapped_column(primary_key=True)
    
    # Включены ли уведомления
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Время напоминаний в минутах
    reminder_minutes: Mapped[Optional[List[int]]] = mapped_column(
        ARRAY(Integer),
        default=[5, 15, 60]
    )
    
    # Типы уведомлений
    new_event_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    event_updated_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    event_cancelled_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # def __repr__(self) -> str:
    #     return f"<NotificationSettings(user_id={self.user_id}, enabled={self.enabled})>"
    
    def is_enabled_for_type(self, notification_type: str) -> bool:
        """Проверяет, включен ли конкретный тип уведомлений"""
        if not self.enabled:
            return False
            
        type_mapping = {
            "new_event": self.new_event_enabled,
            "event_updated": self.event_updated_enabled,
            "event_cancelled": self.event_cancelled_enabled,
            "schedule_reminder": True
        }
        
        return type_mapping.get(notification_type, False)