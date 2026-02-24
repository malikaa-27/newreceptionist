"""
Google Calendar service: availability checking and event creation.
All times are handled in UTC internally.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from ..schemas.schemas import TimeSlot, CreateEventResponse


def _merge_busy(busy_intervals: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    """Merge overlapping busy intervals."""
    if not busy_intervals:
        return []
    sorted_intervals = sorted(busy_intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    for start, end in sorted_intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _free_slots(
    range_start: datetime,
    range_end: datetime,
    busy: List[Tuple[datetime, datetime]],
    duration: timedelta,
) -> List[TimeSlot]:
    """Compute free slots within a range given merged busy intervals."""
    free: List[TimeSlot] = []
    cursor = range_start
    for busy_start, busy_end in busy:
        if cursor + duration <= busy_start:
            slot_end = cursor + duration
            while slot_end <= busy_start:
                free.append(TimeSlot(start=cursor, end=slot_end))
                cursor = slot_end
                slot_end = cursor + duration
        if busy_end > cursor:
            cursor = busy_end
    # Remaining time after last busy block
    slot_end = cursor + duration
    while slot_end <= range_end:
        free.append(TimeSlot(start=cursor, end=slot_end))
        cursor = slot_end
        slot_end = cursor + duration
    return free


def check_availability(
    credentials: Credentials,
    emails: List[str],
    start_range: datetime,
    end_range: datetime,
    duration_minutes: int,
) -> List[TimeSlot]:
    """
    Query Google freebusy API for all emails, merge busy times,
    compute free slots of the requested duration, and return them.
    Raw busy data is never exposed.
    """
    service = build("calendar", "v3", credentials=credentials)

    # Ensure UTC
    start_utc = start_range.astimezone(timezone.utc)
    end_utc = end_range.astimezone(timezone.utc)

    body = {
        "timeMin": start_utc.isoformat(),
        "timeMax": end_utc.isoformat(),
        "items": [{"id": email} for email in emails],
    }
    result = service.freebusy().query(body=body).execute()

    all_busy: List[Tuple[datetime, datetime]] = []
    for cal_data in result.get("calendars", {}).values():
        for period in cal_data.get("busy", []):
            busy_start = datetime.fromisoformat(period["start"].replace("Z", "+00:00"))
            busy_end = datetime.fromisoformat(period["end"].replace("Z", "+00:00"))
            all_busy.append((busy_start, busy_end))

    merged = _merge_busy(all_busy)
    duration = timedelta(minutes=duration_minutes)
    return _free_slots(start_utc, end_utc, merged, duration)


def create_calendar_event(
    credentials: Credentials,
    start: datetime,
    end: datetime,
    attendees: List[str],
    title: str = "Scheduled Meeting",
    description: str = "",
) -> CreateEventResponse:
    """
    Create a Google Calendar event with a Meet link and send invites.
    Returns event_id and meet_link.
    """
    service = build("calendar", "v3", credentials=credentials)

    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)

    event_body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_utc.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_utc.isoformat(), "timeZone": "UTC"},
        "attendees": [{"email": e} for e in attendees],
        "conferenceData": {
            "createRequest": {
                "requestId": f"meet-{start_utc.timestamp()}",
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
        "guestsCanModifyEvent": False,
        "sendUpdates": "all",
    }

    created = (
        service.events()
        .insert(calendarId="primary", body=event_body, conferenceDataVersion=1, sendUpdates="all")
        .execute()
    )

    meet_link = ""
    conference_data = created.get("conferenceData", {})
    for entry_point in conference_data.get("entryPoints", []):
        if entry_point.get("entryPointType") == "video":
            meet_link = entry_point.get("uri", "")
            break

    return CreateEventResponse(
        event_id=created["id"],
        meet_link=meet_link,
        start=start_utc,
        end=end_utc,
    )
