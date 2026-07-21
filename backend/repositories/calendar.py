from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from backend.models.calendar import (
    CalendarEvent,
    CalendarEventCursor,
    CalendarEventPage,
    CalendarSyncWindow,
    TaskCalendarEventLink,
)


class CalendarRepository(Protocol):
    """Persistence port for the user's locally synchronized calendar."""

    async def upsert_events(self, events: Sequence[CalendarEvent]) -> None: ...

    async def list_events(
        self,
        user_id: UUID,
        window: CalendarSyncWindow,
        limit: int,
        cursor: CalendarEventCursor | None,
    ) -> CalendarEventPage: ...

    async def mark_events_cancelled(
        self,
        user_id: UUID,
        provider_calendar_id: str,
        provider_event_ids: Sequence[str],
    ) -> None: ...

    async def get_task_event_link(
        self,
        user_id: UUID,
        task_id: UUID,
    ) -> TaskCalendarEventLink | None: ...

    async def upsert_task_event_link(self, link: TaskCalendarEventLink) -> None: ...
