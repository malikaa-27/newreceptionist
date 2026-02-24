"""
Unit tests for availability intersection logic.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import json

from app.services.google_calendar import (
    _merge_busy_periods,
    _find_free_slots,
    check_availability,
)


def dt(year, month, day, hour, minute=0) -> datetime:
    """Helper to create UTC datetime."""
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class TestMergeBusyPeriods:
    def test_empty_list(self):
        assert _merge_busy_periods([]) == []

    def test_single_period(self):
        periods = [(dt(2024, 2, 1, 9), dt(2024, 2, 1, 10))]
        assert _merge_busy_periods(periods) == periods

    def test_non_overlapping_periods(self):
        periods = [
            (dt(2024, 2, 1, 9), dt(2024, 2, 1, 10)),
            (dt(2024, 2, 1, 11), dt(2024, 2, 1, 12)),
        ]
        result = _merge_busy_periods(periods)
        assert len(result) == 2
        assert result[0] == (dt(2024, 2, 1, 9), dt(2024, 2, 1, 10))
        assert result[1] == (dt(2024, 2, 1, 11), dt(2024, 2, 1, 12))

    def test_overlapping_periods(self):
        periods = [
            (dt(2024, 2, 1, 9), dt(2024, 2, 1, 11)),
            (dt(2024, 2, 1, 10), dt(2024, 2, 1, 12)),
        ]
        result = _merge_busy_periods(periods)
        assert len(result) == 1
        assert result[0] == (dt(2024, 2, 1, 9), dt(2024, 2, 1, 12))

    def test_adjacent_periods(self):
        periods = [
            (dt(2024, 2, 1, 9), dt(2024, 2, 1, 10)),
            (dt(2024, 2, 1, 10), dt(2024, 2, 1, 11)),
        ]
        result = _merge_busy_periods(periods)
        assert len(result) == 1
        assert result[0] == (dt(2024, 2, 1, 9), dt(2024, 2, 1, 11))

    def test_multiple_overlapping(self):
        periods = [
            (dt(2024, 2, 1, 9), dt(2024, 2, 1, 11)),
            (dt(2024, 2, 1, 10), dt(2024, 2, 1, 12)),
            (dt(2024, 2, 1, 11, 30), dt(2024, 2, 1, 13)),
            (dt(2024, 2, 1, 15), dt(2024, 2, 1, 16)),
        ]
        result = _merge_busy_periods(periods)
        assert len(result) == 2
        assert result[0] == (dt(2024, 2, 1, 9), dt(2024, 2, 1, 13))
        assert result[1] == (dt(2024, 2, 1, 15), dt(2024, 2, 1, 16))

    def test_unsorted_periods(self):
        periods = [
            (dt(2024, 2, 1, 14), dt(2024, 2, 1, 15)),
            (dt(2024, 2, 1, 9), dt(2024, 2, 1, 10)),
            (dt(2024, 2, 1, 11), dt(2024, 2, 1, 13)),
        ]
        result = _merge_busy_periods(periods)
        assert len(result) == 3
        assert result[0][0] == dt(2024, 2, 1, 9)


class TestFindFreeSlots:
    def test_fully_free_range(self):
        range_start = dt(2024, 2, 1, 9)
        range_end = dt(2024, 2, 1, 17)
        slots = _find_free_slots(range_start, range_end, [], 60)
        assert len(slots) > 0
        # Each slot should be 60 minutes
        first = slots[0]
        start = datetime.fromisoformat(first["start"])
        end = datetime.fromisoformat(first["end"])
        assert (end - start).total_seconds() == 3600

    def test_fully_busy_range(self):
        range_start = dt(2024, 2, 1, 9)
        range_end = dt(2024, 2, 1, 17)
        busy = [(dt(2024, 2, 1, 8), dt(2024, 2, 1, 18))]
        slots = _find_free_slots(range_start, range_end, busy, 60)
        assert slots == []

    def test_slots_avoid_busy_periods(self):
        range_start = dt(2024, 2, 1, 9)
        range_end = dt(2024, 2, 1, 17)
        busy = [(dt(2024, 2, 1, 10), dt(2024, 2, 1, 14))]
        slots = _find_free_slots(range_start, range_end, busy, 60)
        
        for slot in slots:
            slot_start = datetime.fromisoformat(slot["start"])
            slot_end = datetime.fromisoformat(slot["end"])
            # Slot should not overlap with busy period
            assert not (slot_start < dt(2024, 2, 1, 14) and slot_end > dt(2024, 2, 1, 10))

    def test_duration_filter(self):
        range_start = dt(2024, 2, 1, 9)
        range_end = dt(2024, 2, 1, 10, 30)  # 1.5 hour window
        
        # 60-minute meeting should fit once
        slots_60 = _find_free_slots(range_start, range_end, [], 60)
        assert len(slots_60) >= 1
        
        # 120-minute meeting should not fit
        slots_120 = _find_free_slots(range_start, range_end, [], 120)
        assert slots_120 == []

    def test_slot_count_capped_at_20(self):
        range_start = dt(2024, 2, 1, 0)
        range_end = dt(2024, 2, 8, 0)  # 1 week
        slots = _find_free_slots(range_start, range_end, [], 30)
        assert len(slots) <= 20

    def test_slot_metadata(self):
        range_start = dt(2024, 2, 1, 9)
        range_end = dt(2024, 2, 1, 11)
        slots = _find_free_slots(range_start, range_end, [], 30)
        assert len(slots) > 0
        for slot in slots:
            assert "start" in slot
            assert "end" in slot
            assert "duration_minutes" in slot
            assert slot["duration_minutes"] == 30


class TestCheckAvailability:
    def test_check_availability_returns_slots(self):
        """Test check_availability with mocked Google API."""
        mock_creds = MagicMock()
        
        with patch("app.services.google_calendar.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            
            # Mock freebusy response
            mock_service.freebusy().query().execute.return_value = {
                "calendars": {
                    "user1@example.com": {"busy": []},
                    "user2@example.com": {"busy": []},
                }
            }
            
            start = dt(2024, 2, 5, 9)
            end = dt(2024, 2, 5, 17)
            
            slots = check_availability(
                credentials=mock_creds,
                emails=["user1@example.com", "user2@example.com"],
                start_range=start,
                end_range=end,
                duration_minutes=60,
            )
            
            assert isinstance(slots, list)
            assert len(slots) > 0

    def test_check_availability_with_busy_times(self):
        """Test that busy times are excluded from results."""
        mock_creds = MagicMock()
        
        with patch("app.services.google_calendar.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            
            mock_service.freebusy().query().execute.return_value = {
                "calendars": {
                    "user1@example.com": {
                        "busy": [
                            {
                                "start": "2024-02-05T09:00:00+00:00",
                                "end": "2024-02-05T12:00:00+00:00",
                            }
                        ]
                    },
                }
            }
            
            start = dt(2024, 2, 5, 9)
            end = dt(2024, 2, 5, 13)
            
            slots = check_availability(
                credentials=mock_creds,
                emails=["user1@example.com"],
                start_range=start,
                end_range=end,
                duration_minutes=60,
            )
            
            # Only slot from 12:00 to 13:00 should be available
            for slot in slots:
                slot_start = datetime.fromisoformat(slot["start"])
                assert slot_start >= dt(2024, 2, 5, 12)

    def test_never_exposes_raw_busy_data(self):
        """Verify that raw busy data is never returned."""
        mock_creds = MagicMock()
        
        with patch("app.services.google_calendar.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            
            mock_service.freebusy().query().execute.return_value = {
                "calendars": {
                    "private@example.com": {
                        "busy": [
                            {
                                "start": "2024-02-05T10:00:00+00:00",
                                "end": "2024-02-05T11:00:00+00:00",
                            }
                        ]
                    }
                }
            }
            
            slots = check_availability(
                credentials=mock_creds,
                emails=["private@example.com"],
                start_range=dt(2024, 2, 5, 9),
                end_range=dt(2024, 2, 5, 17),
                duration_minutes=30,
            )
            
            # Result should only have start/end/duration, not raw busy data
            for slot in slots:
                assert "busy" not in slot
                assert set(slot.keys()) == {"start", "end", "duration_minutes"}
