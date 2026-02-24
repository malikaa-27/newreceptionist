from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.api.auth import get_current_user
from app.services.oauth import get_credentials_for_user
from app.services.google_calendar import check_availability, create_calendar_event
from app.schemas.calendar import (
    AvailabilityRequest,
    AvailabilityResponse,
    CreateEventRequest,
    CreateEventResponse,
)
from app.models.meeting import Meeting, MeetingStatus

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

@router.post("/availability", response_model=AvailabilityResponse)
async def get_availability(
    request: AvailabilityRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check availability for participants."""
    credentials = get_credentials_for_user(db, current_user["user_id"])
    if not credentials:
        raise HTTPException(status_code=401, detail="Google Calendar not connected")
    
    try:
        slots = check_availability(
            credentials=credentials,
            emails=request.emails,
            start_range=request.start_range,
            end_range=request.end_range,
            duration_minutes=request.duration_minutes,
        )
        return AvailabilityResponse(slots=slots)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calendar error: {str(e)}")

@router.post("/events", response_model=CreateEventResponse)
async def create_event(
    request: CreateEventRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a calendar event."""
    credentials = get_credentials_for_user(db, current_user["user_id"])
    if not credentials:
        raise HTTPException(status_code=401, detail="Google Calendar not connected")
    
    try:
        result = create_calendar_event(
            credentials=credentials,
            summary=request.summary,
            start=request.start,
            end=request.end,
            attendees=request.attendees,
            description=request.description,
        )
        
        # Save to database
        meeting = Meeting(
            organizer_id=current_user["user_id"],
            participant_email=request.attendees[1] if len(request.attendees) > 1 else request.attendees[0],
            start_time=request.start,
            end_time=request.end,
            google_event_id=result["event_id"],
            meet_link=result.get("meet_link"),
            status=MeetingStatus.CONFIRMED,
        )
        db.add(meeting)
        db.commit()
        
        return CreateEventResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event creation error: {str(e)}")
