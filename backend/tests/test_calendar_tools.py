"""
Integration tests for calendar tool endpoints.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.api.auth import get_current_user


def dt(year, month, day, hour, minute=0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# Override dependencies for testing
def override_get_current_user():
    return {"user_id": 1, "email": "test@example.com"}


def override_get_db():
    mock_db = MagicMock()
    yield mock_db


app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestAvailabilityEndpoint:
    def test_availability_returns_200(self):
        """Test availability endpoint with mocked credentials."""
        with patch("app.api.calendar.get_credentials_for_user") as mock_creds, \
             patch("app.api.calendar.check_availability") as mock_check:
            
            mock_creds.return_value = MagicMock()
            mock_check.return_value = [
                {
                    "start": "2024-02-05T09:00:00+00:00",
                    "end": "2024-02-05T10:00:00+00:00",
                    "duration_minutes": 60,
                }
            ]
            
            response = client.post(
                "/api/calendar/availability",
                json={
                    "emails": ["user1@example.com", "user2@example.com"],
                    "start_range": "2024-02-05T09:00:00Z",
                    "end_range": "2024-02-05T17:00:00Z",
                    "duration_minutes": 60,
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "slots" in data
            assert len(data["slots"]) == 1

    def test_availability_no_credentials(self):
        """Test availability returns 401 when not connected."""
        with patch("app.api.calendar.get_credentials_for_user") as mock_creds:
            mock_creds.return_value = None
            
            response = client.post(
                "/api/calendar/availability",
                json={
                    "emails": ["user@example.com"],
                    "start_range": "2024-02-05T09:00:00Z",
                    "end_range": "2024-02-05T17:00:00Z",
                    "duration_minutes": 30,
                },
            )
            
            assert response.status_code == 401


class TestCreateEventEndpoint:
    def test_create_event_returns_200(self):
        """Test event creation with mocked Google Calendar."""
        with patch("app.api.calendar.get_credentials_for_user") as mock_creds, \
             patch("app.api.calendar.create_calendar_event") as mock_create:
            
            mock_creds.return_value = MagicMock()
            mock_create.return_value = {
                "event_id": "abc123",
                "meet_link": "https://meet.google.com/abc-defg-hij",
                "html_link": "https://calendar.google.com/event/abc123",
                "start": "2024-02-05T09:00:00+00:00",
                "end": "2024-02-05T10:00:00+00:00",
                "attendees": ["user1@example.com", "user2@example.com"],
            }
            
            response = client.post(
                "/api/calendar/events",
                json={
                    "summary": "Test Meeting",
                    "start": "2024-02-05T09:00:00Z",
                    "end": "2024-02-05T10:00:00Z",
                    "attendees": ["user1@example.com", "user2@example.com"],
                    "description": "Test",
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["event_id"] == "abc123"
            assert "meet_link" in data

    def test_create_event_no_credentials(self):
        """Test event creation returns 401 when not connected."""
        with patch("app.api.calendar.get_credentials_for_user") as mock_creds:
            mock_creds.return_value = None
            
            response = client.post(
                "/api/calendar/events",
                json={
                    "summary": "Meeting",
                    "start": "2024-02-05T09:00:00Z",
                    "end": "2024-02-05T10:00:00Z",
                    "attendees": ["user@example.com"],
                },
            )
            
            assert response.status_code == 401
