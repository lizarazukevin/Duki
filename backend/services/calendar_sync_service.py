import asyncio
from uuid import UUID

from backend.adapters.calendar.base import CalendarAdapter
from backend.constants import PRIMARY_CALENDAR_ID
from backend.errors import CalendarRateLimitError
from backend.models.auth import GoogleCredentials
from backend.models.calendar import CalendarFetchResult, CalendarSyncSummary, CalendarSyncWindow
from backend.repositories.auth import AuthRepository
from backend.repositories.calendar import CalendarRepository

CALENDAR_FETCH_ATTEMPTS = 2
CALENDAR_RETRY_DELAY_SECONDS = 0.25


class CalendarSyncService:
    """Synchronize one user's primary calendar into private local storage."""

    def __init__(
        self,
        calendar_adapter: CalendarAdapter,
        auth_repository: AuthRepository,
        calendar_repository: CalendarRepository,
    ) -> None:
        self._calendar_adapter = calendar_adapter
        self._auth_repository = auth_repository
        self._calendar_repository = calendar_repository

    async def sync(
        self,
        user_id: UUID,
        window: CalendarSyncWindow,
    ) -> CalendarSyncSummary:
        credentials = await self._auth_repository.get_google_credentials(user_id)
        fetched = await self._fetch_with_retry(credentials, window)
        if fetched.refreshed_credentials is not None:
            await self._auth_repository.save_google_credentials(fetched.refreshed_credentials)
        await self._calendar_repository.upsert_events(fetched.events)
        await self._calendar_repository.mark_events_cancelled(
            user_id=user_id,
            provider_calendar_id=PRIMARY_CALENDAR_ID,
            provider_event_ids=fetched.cancelled_event_ids,
        )
        return CalendarSyncSummary(
            events_upserted=len(fetched.events),
            events_cancelled=len(fetched.cancelled_event_ids),
        )

    async def _fetch_with_retry(
        self,
        credentials: GoogleCredentials,
        window: CalendarSyncWindow,
    ) -> CalendarFetchResult:
        for attempt in range(CALENDAR_FETCH_ATTEMPTS):
            try:
                return await self._calendar_adapter.list_events(
                    credentials=credentials,
                    start_time=window.start_time,
                    end_time=window.end_time,
                    calendar_id=PRIMARY_CALENDAR_ID,
                )
            except CalendarRateLimitError:
                if attempt + 1 == CALENDAR_FETCH_ATTEMPTS:
                    raise
                await asyncio.sleep(CALENDAR_RETRY_DELAY_SECONDS)
        raise AssertionError("Calendar fetch attempts must be positive")
