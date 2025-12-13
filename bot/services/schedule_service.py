from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

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
                event_copy = event.copy()
                event_copy["start_time_local"] = self._convert_time_for_user(
                    event["start_time"], 
                    event.get("creator_timezone", "UTC+3"),
                    user_timezone
                )
                event_copy["end_time_local"] = self._convert_time_for_user(
                    event["end_time"],
                    event.get("creator_timezone", "UTC+3"),
                    user_timezone
                )
                role_events.append(event_copy)
            elif role in event["visibility"]:
                event_copy = event.copy()
                event_copy["start_time_local"] = self._convert_time_for_user(
                    event["start_time"],
                    event.get("creator_timezone", "UTC+3"),
                    user_timezone
                )
                event_copy["end_time_local"] = self._convert_time_for_user(
                    event["end_time"],
                    event.get("creator_timezone", "UTC+3"),
                    user_timezone
                )
                role_events.append(event_copy)
        
        return role_events
    
    def _convert_time_for_user(
        self, 
        event_time: datetime, 
        event_timezone: str, 
        user_timezone: str
    ) -> datetime:
        event_offset = TIMEZONE_OFFSETS.get(event_timezone, 3)
        user_offset = TIMEZONE_OFFSETS.get(user_timezone, 3)
        offset_diff = user_offset - event_offset
        return event_time + timedelta(hours=offset_diff)
    
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
        start_time = event.get("start_time_local", event["start_time"])
        end_time = event.get("end_time_local", event["end_time"])
        
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

schedule_service = ScheduleService()