from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.models.meeting import MeetingStatus

class MeetingCreate(BaseModel):
    participant_email: EmailStr
    start_time: datetime
    end_time: datetime
    google_event_id: Optional[str] = None
    meet_link: Optional[str] = None

class MeetingResponse(BaseModel):
    id: int
    organizer_id: int
    participant_email: str
    start_time: datetime
    end_time: datetime
    google_event_id: Optional[str]
    meet_link: Optional[str]
    status: MeetingStatus
    created_at: datetime
    
    class Config:
        from_attributes = True
