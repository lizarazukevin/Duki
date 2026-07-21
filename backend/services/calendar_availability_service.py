from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from backend.models.calendar import (
    CalendarEvent,
    CalendarEventStatus,
    CalendarEventTransparency,
    CalendarFreeBlock,
    CalendarSyncWindow,
)
from backend.repositories.calendar import CalendarRepository

CALENDAR_PAGE_SIZE = 100


class CalendarAvailabilityService:
    """Derive usable free blocks from a user's private cached calendar."""

    def __init__(self, calendar_repository: CalendarRepository) -> None:
        self._calendar_repository = calendar_repository

    async def list_free_blocks(
        self,
        user_id: UUID,
        window: CalendarSyncWindow,
        minimum_minutes: int,
    ) -> tuple[CalendarFreeBlock, ...]:
        events = await self._load_events(user_id, window)
        return derive_free_blocks(events, window, minimum_minutes)

    async def _load_events(
        self,
        user_id: UUID,
        window: CalendarSyncWindow,
    ) -> tuple[CalendarEvent, ...]:
        events: list[CalendarEvent] = []
        cursor = None
        while True:
            page = await self._calendar_repository.list_events(
                user_id,
                window,
                CALENDAR_PAGE_SIZE,
                cursor,
            )
            events.extend(item.event for item in page.items)
            if page.next_cursor is None:
                return tuple(events)
            cursor = page.next_cursor


def derive_free_blocks(
    events: Sequence[CalendarEvent],
    window: CalendarSyncWindow,
    minimum_minutes: int,
) -> tuple[CalendarFreeBlock, ...]:
    """Return deterministic gaps after clipping and merging blocking events."""
    if minimum_minutes <= 0:
        raise ValueError("Minimum free-block duration must be positive")
    minimum_duration = timedelta(minutes=minimum_minutes)
    intervals = sorted(
        (
            (max(event.start_time, window.start_time), min(event.end_time, window.end_time))
            for event in events
            if event.status is not CalendarEventStatus.CANCELLED
            and event.transparency is CalendarEventTransparency.OPAQUE
            and event.end_time > window.start_time
            and event.start_time < window.end_time
        ),
        key=lambda interval: interval[0],
    )
    merged: list[tuple[datetime, datetime]] = []
    for start_time, end_time in intervals:
        if end_time <= start_time:
            continue
        if merged and start_time <= merged[-1][1]:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end_time))
        else:
            merged.append((start_time, end_time))

    blocks: list[CalendarFreeBlock] = []
    available_from = window.start_time
    for busy_start, busy_end in merged:
        if busy_start - available_from >= minimum_duration:
            blocks.append(CalendarFreeBlock(available_from, busy_start))
        available_from = max(available_from, busy_end)
    if window.end_time - available_from >= minimum_duration:
        blocks.append(CalendarFreeBlock(available_from, window.end_time))
    return tuple(blocks)
