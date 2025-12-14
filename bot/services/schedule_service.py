from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from aiogram import Bot

class EventVisibility(Enum):
    ALL = "all"
    PARTICIPANT = "participant"
    ORGANIZER = "organizer"
    MENTOR = "mentor"
    VOLUNTEER = "volunteer"

TIMEZONE_OFFSETS = {
    "UTC+3": 3,
    "UTC+4": 4,
    "UTC+5": 5,
    "UTC+6": 6,
    "UTC+7": 7,
    "UTC+8": 8,
    "UTC+9": 9,
    "UTC+10": 10,
}

schedule_storage = {
    "events": [],
    "last_event_id": 0
}

class ScheduleService:
    def __init__(self):
        self.events = schedule_storage["events"]
        self.last_event_id = schedule_storage["last_event_id"]
    
    def _save_changes(self):
        schedule_storage["events"] = self.events
        schedule_storage["last_event_id"] = self.last_event_id
    
    def add_event(
        self,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        visibility: List[str],
        location: str = "",
        created_by: str = "",
        creator_timezone: str = "UTC+3"
    ) -> Dict[str, Any]:
        self.last_event_id += 1

        event = {
            "id": self.last_event_id,
            "title": title,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "visibility": visibility,
            "created_by": created_by,
            "creator_timezone": creator_timezone,
            "created_at": datetime.now()
        }

        self.events.append(event)
        self._save_changes()
        return event
    
    def get_events_for_role(
        self,
        role: str,
        user_timezone: str = "UTC+3",
        include_all: bool = True
    ) -> List[Dict[str, Any]]:
        role_events = []
    
        for event in sorted(self.events, key=lambda x: x["start_time"]):
            if include_all and "all" in event["visibility"]:
                role_events.append({
                    **event,
                    "start_time_local": self._convert_time_for_user(
                        event["start_time"], 
                        event.get("creator_timezone", "UTC+3"),
                        user_timezone
                    ),
                    "end_time_local": self._convert_time_for_user(
                        event["end_time"],
                        event.get("creator_timezone", "UTC+3"),
                        user_timezone
                    )
                })
            elif role in event["visibility"]:
                role_events.append({
                    **event,
                    "start_time_local": self._convert_time_for_user(
                        event["start_time"],
                        event.get("creator_timezone", "UTC+3"),
                        user_timezone
                    ),
                    "end_time_local": self._convert_time_for_user(
                        event["end_time"],
                        event.get("creator_timezone", "UTC+3"),
                        user_timezone
                    )
                })
    
        return role_events
    
    def _convert_time_for_user(
        self, 
        event_time: datetime, 
        event_timezone: str, 
        user_timezone: str
    ) -> datetime:
    
        event_offset = TIMEZONE_OFFSETS.get(event_timezone, 3)
        user_offset = TIMEZONE_OFFSETS.get(user_timezone, 3)
    
        time_diff = user_offset - event_offset
        return event_time + timedelta(hours=time_diff)
    
    def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        for event in self.events:
            if event["id"] == event_id:
                return event
        return None
    
    def update_event(self, event_id: int, **kwargs) -> bool:
        event = self.get_event_by_id(event_id)
        if not event:
            return False
        
        for key, value in kwargs.items():
            if key in event:
                event[key] = value
        
        self._save_changes()
        return True
    
    def delete_event(self, event_id: int) -> bool:
        event = self.get_event_by_id(event_id)
        if not event:
            return False
        
        self.events.remove(event)
        self._save_changes()
        return True
    
    def get_all_events(self) -> List[Dict[str, Any]]:
        return sorted(self.events, key=lambda x: x["start_time"])
    
    def format_event_for_display(
        self, 
        event: Dict[str, Any], 
        user_timezone: str = "UTC+3"
    ) -> str:

        start_time = self._convert_time_for_user(
            event["start_time"],
            event.get("creator_timezone", "UTC+3"),
            user_timezone
        )
        end_time = self._convert_time_for_user(
            event["end_time"],
            event.get("creator_timezone", "UTC+3"),
            user_timezone
        )
        
        start = start_time.strftime("%d.%m %H:%M")
        end = end_time.strftime("%H:%M")
        
        text = (
            f"📅 <b>{event['title']}</b>\n"
            f"🕒 {start} - {end}\n"
        )
        
        if event.get("location"):
            text += f"📍 {event['location']}\n"
        
        if event.get("description"):
            text += f"\n{event['description']}\n"
        
        visibility = event.get("visibility", [])
        if "all" in visibility:
            text += "\n<i>Для всех участников</i>"
        else:
            roles_display = []
            role_emojis = {
                "participant": "👤",
                "organizer": "🎪",
                "mentor": "🧠",
                "volunteer": "🤝"
            }
            
            for role in visibility:
                if role in role_emojis:
                    roles_display.append(role_emojis[role])
            
            if roles_display:
                text += f"\n<i>Для: {' '.join(roles_display)}</i>"
        
        return text
    
    async def add_event_with_notification(
        self,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        visibility: List[str],
        location: str = "",
        created_by: str = "",
        creator_timezone: str = "UTC+3",
        bot: Optional[Bot] = None,
        temp_users_storage: Optional[Dict] = None
    ) -> Dict[str, Any]:
        
        event = self.add_event(
            title, description, start_time, end_time,
            visibility, location, created_by, creator_timezone
        )
        
        if bot and temp_users_storage:
            from bot.handlers.notifications import notify_new_event
            await notify_new_event(bot, event, temp_users_storage)
        
        return event
    
    async def update_event_with_notification(
        self,
        event_id: int,
        bot: Optional[Bot] = None,
        temp_users_storage: Optional[Dict] = None,
        **kwargs
    ) -> bool:
        
        old_event = self.get_event_by_id(event_id)
        if not old_event:
            return False
        
        changes = {}
        for key, value in kwargs.items():
            if key in old_event and old_event[key] != value:
                if key != "visibility":
                    changes[key] = value
        
        success = self.update_event(event_id, **kwargs)
        
        if success and changes and bot and temp_users_storage:
            new_event = self.get_event_by_id(event_id)
            from bot.handlers.notifications import notify_event_updated
            await notify_event_updated(bot, new_event, changes, temp_users_storage)
        
        return success
    
    async def delete_event_with_notification(
        self,
        event_id: int,
        bot: Optional[Bot] = None,
        temp_users_storage: Optional[Dict] = None
    ) -> bool:
        event = self.get_event_by_id(event_id)
        if not event:
            return False
        
        success = self.delete_event(event_id)
        
        if success and bot and temp_users_storage:
            from bot.handlers.notifications import notify_event_cancelled  # Исправленный импорт
            await notify_event_cancelled(bot, event, temp_users_storage)
        
        return success

schedule_service = ScheduleService()