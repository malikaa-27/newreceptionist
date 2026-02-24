"""
Unit tests for availability intersection logic in calendar_service.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from datetime import datetime, timedelta, timezone
import pytest

from app.services.calendar_service import _merge_busy, _free_slots
from app.schemas.schemas import TimeSlot


UTC = timezone.utc


def dt(hour: int, minute: int = 0, day: int = 15) -> datetime:
    return datetime(2024, 1, day, hour, minute, tzinfo=UTC)


# ── _merge_busy ────────────────────────────────────────────────────────────────

class TestMergeBusy:
    def test_empty(self):
        assert _merge_busy([]) == []

    def test_single(self):
        assert _merge_busy([(dt(9), dt(10))]) == [(dt(9), dt(10))]

    def test_no_overlap(self):
        result = _merge_busy([(dt(9), dt(10)), (dt(11), dt(12))])
        assert result == [(dt(9), dt(10)), (dt(11), dt(12))]

    def test_adjacent(self):
        result = _merge_busy([(dt(9), dt(10)), (dt(10), dt(11))])
        assert result == [(dt(9), dt(11))]

    def test_overlap(self):
        result = _merge_busy([(dt(9), dt(11)), (dt(10), dt(12))])
        assert result == [(dt(9), dt(12))]

    def test_contained(self):
        result = _merge_busy([(dt(9), dt(13)), (dt(10), dt(11))])
        assert result == [(dt(9), dt(13))]

    def test_multiple_overlapping(self):
        intervals = [(dt(9), dt(11)), (dt(10), dt(12)), (dt(14), dt(15))]
        result = _merge_busy(intervals)
        assert result == [(dt(9), dt(12)), (dt(14), dt(15))]

    def test_unsorted_input(self):
        result = _merge_busy([(dt(11), dt(12)), (dt(9), dt(10))])
        assert result == [(dt(9), dt(10)), (dt(11), dt(12))]


# ── _free_slots ────────────────────────────────────────────────────────────────

class TestFreeSlots:
    def test_no_busy(self):
        """Entire range is free → slots fill the window."""
        slots = _free_slots(dt(9), dt(11), [], timedelta(hours=1))
        assert len(slots) == 2
        assert slots[0] == TimeSlot(start=dt(9), end=dt(10))
        assert slots[1] == TimeSlot(start=dt(10), end=dt(11))

    def test_fully_busy(self):
        """Range entirely occupied → no slots."""
        slots = _free_slots(dt(9), dt(11), [(dt(9), dt(11))], timedelta(hours=1))
        assert slots == []

    def test_gap_too_small(self):
        """Free gap smaller than duration → no slot."""
        slots = _free_slots(
            dt(9), dt(11), [(dt(9, 30), dt(10, 30))], timedelta(hours=1)
        )
        assert slots == []

    def test_busy_in_middle(self):
        """Busy block in the middle splits free time into two windows."""
        slots = _free_slots(
            dt(8), dt(18),
            [(dt(10), dt(14))],
            timedelta(hours=1),
        )
        starts = [s.start for s in slots]
        # Before busy: 8-9, 9-10; after busy: 14-15, 15-16, 16-17, 17-18
        assert dt(8) in starts
        assert dt(9) in starts
        assert dt(14) in starts
        assert dt(10) not in starts
        assert dt(13) not in starts

    def test_30_minute_slots(self):
        """30-minute slots in a 2-hour window with no busy time."""
        slots = _free_slots(dt(9), dt(11), [], timedelta(minutes=30))
        assert len(slots) == 4

    def test_busy_at_start(self):
        """Busy at the very start → free portion after it."""
        slots = _free_slots(dt(9), dt(12), [(dt(9), dt(10))], timedelta(hours=1))
        assert len(slots) == 2
        assert slots[0].start == dt(10)

    def test_busy_at_end(self):
        """Busy at the very end → only one free slot before it."""
        slots = _free_slots(dt(9), dt(12), [(dt(11), dt(12))], timedelta(hours=1))
        assert len(slots) == 2
        assert slots[-1].end == dt(11)

    def test_multiple_busy_blocks(self):
        """Multiple separate busy blocks leave distinct free windows."""
        busy = [(dt(9, 30), dt(10)), (dt(11), dt(11, 30))]
        slots = _free_slots(dt(9), dt(12), busy, timedelta(minutes=30))
        slot_starts = [s.start for s in slots]
        # 9:00-9:30 is free (30 min)
        assert dt(9) in slot_starts
        # 10:00-10:30, 10:30-11:00 are free
        assert dt(10) in slot_starts
        assert dt(10, 30) in slot_starts
        # 11:30-12:00 is free
        assert dt(11, 30) in slot_starts
