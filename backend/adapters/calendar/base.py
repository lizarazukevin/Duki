from datetime import datetime
from typing import Protocol

from backend.models.auth import GoogleCredentials
from backend.models.calendar import CalendarFetchResult


class CalendarAdapter(Protocol):
    """Port for reading a user's events from an external calendar provider."""

    async def list_events(
        self,
        credentials: GoogleCredentials,
        start_time: datetime,
        end_time: datetime,
        calendar_id: str = "primary",
    ) -> CalendarFetchResult: ...
