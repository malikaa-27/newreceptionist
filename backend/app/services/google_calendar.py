from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta, timezone
from typing import Optional
import pytz

from app.config import get_settings

settings = get_settings()

def _build_calendar_service(credentials: Credentials):
    return build("calendar", "v3", credentials=credentials)

def check_availability(
    credentials: Credentials,
    emails: list[str],
    start_range: datetime,
    end_range: datetime,
    duration_minutes: int,
) -> list[dict]:
    """
    Check availability of multiple participants using freebusy query.
    Returns list of available time slots (never exposes raw busy data).
    """
    service = _build_calendar_service(credentials)
    
    # Ensure UTC
    if start_range.tzinfo is None:
        start_range = start_range.replace(tzinfo=timezone.utc)
    if end_range.tzinfo is None:
        end_range = end_range.replace(tzinfo=timezone.utc)
    
    body = {
        "timeMin": start_range.isoformat(),
        "timeMax": end_range.isoformat(),
        "timeZone": "UTC",
        "items": [{"id": email} for email in emails],
    }
    
    freebusy_result = service.freebusy().query(body=body).execute()
    
    # Collect all busy periods across all calendars
    all_busy: list[tuple[datetime, datetime]] = []
    for calendar_data in freebusy_result.get("calendars", {}).values():
        for busy_period in calendar_data.get("busy", []):
            busy_start = datetime.fromisoformat(busy_period["start"].replace("Z", "+00:00"))
            busy_end = datetime.fromisoformat(busy_period["end"].replace("Z", "+00:00"))
            all_busy.append((busy_start, busy_end))
    
    # Merge overlapping busy periods
    merged_busy = _merge_busy_periods(all_busy)
    
    # Find free slots
    free_slots = _find_free_slots(
        start_range, end_range, merged_busy, duration_minutes
    )
    
    return free_slots

def _merge_busy_periods(
    busy_periods: list[tuple[datetime, datetime]]
) -> list[tuple[datetime, datetime]]:
    """Merge overlapping busy time periods."""
    if not busy_periods:
        return []
    
    sorted_busy = sorted(busy_periods, key=lambda x: x[0])
    merged = [sorted_busy[0]]
    
    for current_start, current_end in sorted_busy[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))
    
    return merged

def _find_free_slots(
    range_start: datetime,
    range_end: datetime,
    busy_periods: list[tuple[datetime, datetime]],
    duration_minutes: int,
) -> list[dict]:
    """Find free slots in a time range given busy periods."""
    duration = timedelta(minutes=duration_minutes)
    free_slots = []
    
    # Slot generation with 30-minute granularity
    slot_start = range_start
    
    while slot_start + duration <= range_end:
        slot_end = slot_start + duration
        
        # Check if slot overlaps with any busy period
        is_free = True
        for busy_start, busy_end in busy_periods:
            if slot_start < busy_end and slot_end > busy_start:
                is_free = False
                # Jump to end of this busy period
                slot_start = busy_end
                break
        
        if is_free:
            free_slots.append({
                "start": slot_start.isoformat(),
                "end": slot_end.isoformat(),
                "duration_minutes": duration_minutes,
            })
            slot_start += timedelta(minutes=30)
        
        if len(free_slots) >= 20:  # Cap at 20 slots
            break
    
    return free_slots

def create_calendar_event(
    credentials: Credentials,
    summary: str,
    start: datetime,
    end: datetime,
    attendees: list[str],
    description: str = "",
    timezone_str: str = "UTC",
) -> dict:
    """
    Create a Google Calendar event with a Meet link.
    Returns event_id and meet_link.
    """
    service = _build_calendar_service(credentials)
    
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    
    event_body = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": timezone_str,
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": timezone_str,
        },
        "attendees": [{"email": email} for email in attendees],
        "conferenceData": {
            "createRequest": {
                "requestId": f"meet-{start.timestamp():.0f}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 10},
            ],
        },
        "sendUpdates": "all",
    }
    
    event = service.events().insert(
        calendarId="primary",
        body=event_body,
        conferenceDataVersion=1,
        sendNotifications=True,
    ).execute()
    
    meet_link = None
    if "conferenceData" in event:
        entry_points = event["conferenceData"].get("entryPoints", [])
        for ep in entry_points:
            if ep.get("entryPointType") == "video":
                meet_link = ep.get("uri")
                break
    
    return {
        "event_id": event["id"],
        "meet_link": meet_link,
        "html_link": event.get("htmlLink"),
        "start": event["start"]["dateTime"],
        "end": event["end"]["dateTime"],
        "attendees": [a["email"] for a in event.get("attendees", [])],
    }
