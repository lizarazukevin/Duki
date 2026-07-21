from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from backend.models.calendar import CalendarEvent


class CalendarRepository(Protocol):
    """Persistence port for the user's locally synchronized calendar."""

    async def upsert_events(self, events: Sequence[CalendarEvent]) -> None: ...

    async def mark_events_cancelled(
        self,
        user_id: UUID,
        provider_calendar_id: str,
        provider_event_ids: Sequence[str],
    ) -> None: ...
