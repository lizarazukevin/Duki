from collections.abc import Sequence
from datetime import UTC, datetime

import httpx

from backend.errors import CalendarPersistenceError
from backend.models.calendar import CalendarEvent
from backend.repositories.calendar import CalendarRepository


class SupabaseCalendarRepository(CalendarRepository):
    """Persist normalized calendar events through Supabase PostgREST."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        secret_key: str,
    ) -> None:
        self._http_client = http_client
        self._events_url = f"{supabase_url.rstrip('/')}/rest/v1/calendar_events"
        self._headers = {
            "apikey": secret_key,
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }

    async def upsert_events(self, events: Sequence[CalendarEvent]) -> None:
        if not events:
            return
        synced_at = datetime.now(UTC).isoformat()
        payload = [self._serialize_event(event, synced_at) for event in events]
        try:
            response = await self._http_client.post(
                self._events_url,
                params={
                    "on_conflict": "user_id,provider_calendar_id,provider_event_id",
                },
                headers=self._headers,
                json=payload,
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as error:
            raise CalendarPersistenceError("Calendar events could not be saved") from error
        if response.status_code >= 400:
            raise CalendarPersistenceError("Calendar events could not be saved")

    @staticmethod
    def _serialize_event(event: CalendarEvent, synced_at: str) -> dict[str, object]:
        return {
            "user_id": str(event.user_id),
            "provider_event_id": event.provider_event_id,
            "provider_calendar_id": event.provider_calendar_id,
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "is_all_day": event.is_all_day,
            "status": event.status.value,
            "transparency": event.transparency.value,
            "provider_updated_at": event.provider_updated_at.isoformat(),
            "synced_at": synced_at,
            "updated_at": synced_at,
        }
