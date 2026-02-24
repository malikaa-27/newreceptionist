"""
Integration tests for create_calendar_event with a mocked Google API.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.calendar_service import create_calendar_event, check_availability
from app.schemas.schemas import TimeSlot

UTC = timezone.utc


def _make_mock_creds():
    creds = MagicMock()
    creds.token = "fake-token"
    creds.expired = False
    return creds


def _make_events_service(event_response: dict):
    """Build a mock googleapiclient service that returns event_response."""
    mock_insert = MagicMock()
    mock_insert.execute.return_value = event_response

    mock_events = MagicMock()
    mock_events.insert.return_value = mock_insert

    mock_service = MagicMock()
    mock_service.events.return_value = mock_events
    return mock_service


def _make_freebusy_service(busy_data: dict):
    """Build a mock service that returns busy_data from freebusy().query()."""
    mock_query = MagicMock()
    mock_query.execute.return_value = busy_data

    mock_freebusy = MagicMock()
    mock_freebusy.query.return_value = mock_query

    mock_service = MagicMock()
    mock_service.freebusy.return_value = mock_freebusy
    return mock_service


class TestCreateCalendarEvent:
    def test_creates_event_and_returns_meet_link(self):
        """create_calendar_event returns event_id and meet_link from API response."""
        fake_event = {
            "id": "abc123",
            "conferenceData": {
                "entryPoints": [
                    {"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"},
                    {"entryPointType": "phone", "uri": "tel:+1234567890"},
                ]
            },
        }
        creds = _make_mock_creds()
        with patch(
            "app.services.calendar_service.build",
            return_value=_make_events_service(fake_event),
        ):
            result = create_calendar_event(
                credentials=creds,
                start=datetime(2024, 1, 15, 14, 0, tzinfo=UTC),
                end=datetime(2024, 1, 15, 15, 0, tzinfo=UTC),
                attendees=["alice@example.com", "bob@example.com"],
                title="Test Meeting",
            )

        assert result.event_id == "abc123"
        assert result.meet_link == "https://meet.google.com/abc-defg-hij"

    def test_no_meet_link_when_not_present(self):
        """create_calendar_event returns empty meet_link when conferenceData is missing."""
        fake_event = {"id": "xyz789", "conferenceData": {"entryPoints": []}}
        creds = _make_mock_creds()
        with patch(
            "app.services.calendar_service.build",
            return_value=_make_events_service(fake_event),
        ):
            result = create_calendar_event(
                credentials=creds,
                start=datetime(2024, 1, 15, 14, 0, tzinfo=UTC),
                end=datetime(2024, 1, 15, 15, 0, tzinfo=UTC),
                attendees=["alice@example.com"],
            )

        assert result.meet_link == ""

    def test_correct_attendees_sent(self):
        """Verify that the attendees list is forwarded to events.insert."""
        fake_event = {"id": "e1", "conferenceData": {"entryPoints": []}}
        creds = _make_mock_creds()
        mock_service = _make_events_service(fake_event)
        with patch("app.services.calendar_service.build", return_value=mock_service):
            create_calendar_event(
                credentials=creds,
                start=datetime(2024, 1, 15, 14, 0, tzinfo=UTC),
                end=datetime(2024, 1, 15, 15, 0, tzinfo=UTC),
                attendees=["a@example.com", "b@example.com"],
            )

        call_kwargs = mock_service.events().insert.call_args[1]
        body = call_kwargs["body"]
        attendee_emails = [a["email"] for a in body["attendees"]]
        assert "a@example.com" in attendee_emails
        assert "b@example.com" in attendee_emails


class TestCheckAvailabilityIntegration:
    def test_returns_free_slots_excluding_busy(self):
        """check_availability correctly excludes busy times from freebusy response."""
        busy_response = {
            "calendars": {
                "alice@example.com": {
                    "busy": [
                        {"start": "2024-01-15T09:00:00Z", "end": "2024-01-15T10:00:00Z"}
                    ]
                },
                "bob@example.com": {"busy": []},
            }
        }
        creds = _make_mock_creds()
        with patch(
            "app.services.calendar_service.build",
            return_value=_make_freebusy_service(busy_response),
        ):
            slots = check_availability(
                credentials=creds,
                emails=["alice@example.com", "bob@example.com"],
                start_range=datetime(2024, 1, 15, 9, 0, tzinfo=UTC),
                end_range=datetime(2024, 1, 15, 12, 0, tzinfo=UTC),
                duration_minutes=60,
            )

        # 9-10 is busy; free slots are 10-11 and 11-12
        assert len(slots) == 2
        assert slots[0].start == datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
        assert slots[1].start == datetime(2024, 1, 15, 11, 0, tzinfo=UTC)

    def test_no_slots_when_fully_booked(self):
        """check_availability returns empty list when no free time available."""
        busy_response = {
            "calendars": {
                "alice@example.com": {
                    "busy": [
                        {"start": "2024-01-15T09:00:00Z", "end": "2024-01-15T12:00:00Z"}
                    ]
                }
            }
        }
        creds = _make_mock_creds()
        with patch(
            "app.services.calendar_service.build",
            return_value=_make_freebusy_service(busy_response),
        ):
            slots = check_availability(
                credentials=creds,
                emails=["alice@example.com"],
                start_range=datetime(2024, 1, 15, 9, 0, tzinfo=UTC),
                end_range=datetime(2024, 1, 15, 12, 0, tzinfo=UTC),
                duration_minutes=60,
            )

        assert slots == []

    def test_merged_busy_across_participants(self):
        """Busy times from multiple participants are merged before computing free slots."""
        busy_response = {
            "calendars": {
                "alice@example.com": {
                    "busy": [
                        {"start": "2024-01-15T09:00:00Z", "end": "2024-01-15T10:30:00Z"}
                    ]
                },
                "bob@example.com": {
                    "busy": [
                        {"start": "2024-01-15T10:00:00Z", "end": "2024-01-15T11:00:00Z"}
                    ]
                },
            }
        }
        creds = _make_mock_creds()
        with patch(
            "app.services.calendar_service.build",
            return_value=_make_freebusy_service(busy_response),
        ):
            slots = check_availability(
                credentials=creds,
                emails=["alice@example.com", "bob@example.com"],
                start_range=datetime(2024, 1, 15, 9, 0, tzinfo=UTC),
                end_range=datetime(2024, 1, 15, 13, 0, tzinfo=UTC),
                duration_minutes=60,
            )

        # Merged busy: 9:00-11:00; free: 11:00-12:00, 12:00-13:00
        assert len(slots) == 2
        assert slots[0].start == datetime(2024, 1, 15, 11, 0, tzinfo=UTC)
