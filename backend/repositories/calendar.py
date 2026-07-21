from collections.abc import Sequence
from typing import Protocol

from backend.models.calendar import CalendarEvent


class CalendarRepository(Protocol):
    """Persistence port for the user's locally synchronized calendar."""

    async def upsert_events(self, events: Sequence[CalendarEvent]) -> None: ...
