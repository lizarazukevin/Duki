from datetime import datetime
from typing import Protocol

from backend.constants import PRIMARY_CALENDAR_ID
from backend.models.auth import GoogleCredentials
from backend.models.calendar import CalendarFetchResult, CalendarWriteResult


class CalendarAdapter(Protocol):
    """Port for reading and writing external calendar events."""

    async def list_events(
        self,
        credentials: GoogleCredentials,
        start_time: datetime,
        end_time: datetime,
        calendar_id: str = PRIMARY_CALENDAR_ID,
    ) -> CalendarFetchResult: ...

    async def create_event(
        self,
        credentials: GoogleCredentials,
        title: str,
        description: str | None,
        start_time: datetime,
        end_time: datetime,
        calendar_id: str = PRIMARY_CALENDAR_ID,
    ) -> CalendarWriteResult: ...

    async def update_event(
        self,
        credentials: GoogleCredentials,
        provider_event_id: str,
        title: str,
        description: str | None,
        start_time: datetime,
        end_time: datetime,
        calendar_id: str = PRIMARY_CALENDAR_ID,
    ) -> CalendarWriteResult: ...
