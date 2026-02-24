from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, UUID4, ConfigDict


# ── Auth / User ──────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: UUID4
    email: str
    name: str
    timezone: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TimeSlot(BaseModel):
    start: datetime
    end: datetime


class CheckAvailabilityRequest(BaseModel):
    emails: List[str]
    start_range: datetime
    end_range: datetime
    duration_minutes: int


class CheckAvailabilityResponse(BaseModel):
    available_slots: List[TimeSlot]


class CreateEventRequest(BaseModel):
    start: datetime
    end: datetime
    attendees: List[str]
    title: Optional[str] = "Scheduled Meeting"
    description: Optional[str] = ""


class CreateEventResponse(BaseModel):
    event_id: str
    meet_link: str
    start: datetime
    end: datetime


# ── Agent ─────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str          # "user" | "assistant" | "tool"
    content: str
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None


class AgentRequest(BaseModel):
    session_id: str
    message: str
    timezone: Optional[str] = "UTC"


class AgentResponse(BaseModel):
    message: str
    session_id: str
    tool_calls: Optional[List[dict]] = None
    meeting_confirmed: bool = False
    meeting_details: Optional[CreateEventResponse] = None


# ── Meeting ───────────────────────────────────────────────────────────────────

class MeetingOut(BaseModel):
    id: UUID4
    participant_email: str
    start_time: datetime
    end_time: datetime
    google_event_id: Optional[str]
    meet_link: Optional[str]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
