"""
Calendar tool endpoints: check availability and create events.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.google_auth import get_credentials
from ..services.calendar_service import check_availability, create_calendar_event
from ..schemas.schemas import (
    CheckAvailabilityRequest,
    CheckAvailabilityResponse,
    CreateEventRequest,
    CreateEventResponse,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])
_SESSION_KEY = "user_id"


def _require_user(request: Request):
    user_id = request.session.get(_SESSION_KEY)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


@router.post("/availability", response_model=CheckAvailabilityResponse)
async def availability(
    body: CheckAvailabilityRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _require_user(request)
    creds = get_credentials(db, user_id)
    if not creds:
        raise HTTPException(status_code=401, detail="No credentials found. Please log in again.")

    slots = check_availability(
        credentials=creds,
        emails=body.emails,
        start_range=body.start_range,
        end_range=body.end_range,
        duration_minutes=body.duration_minutes,
    )
    return CheckAvailabilityResponse(available_slots=slots)


@router.post("/events", response_model=CreateEventResponse)
async def create_event(
    body: CreateEventRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _require_user(request)
    creds = get_credentials(db, user_id)
    if not creds:
        raise HTTPException(status_code=401, detail="No credentials found. Please log in again.")

    event = create_calendar_event(
        credentials=creds,
        start=body.start,
        end=body.end,
        attendees=body.attendees,
        title=body.title or "Scheduled Meeting",
        description=body.description or "",
    )
    return event
