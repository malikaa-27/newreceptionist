from pydantic import BaseModel
from datetime import datetime
from typing import List

class AvailabilityRequest(BaseModel):
    emails: List[str]
    start_range: datetime
    end_range: datetime
    duration_minutes: int = 30

class TimeSlot(BaseModel):
    start: str
    end: str
    duration_minutes: int

class AvailabilityResponse(BaseModel):
    slots: List[TimeSlot]

class CreateEventRequest(BaseModel):
    summary: str
    start: datetime
    end: datetime
    attendees: List[str]
    description: str = ""

class CreateEventResponse(BaseModel):
    event_id: str
    meet_link: str | None
    html_link: str | None
    start: str
    end: str
    attendees: List[str]
