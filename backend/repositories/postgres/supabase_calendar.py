import json
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import httpx

from backend.errors import CalendarPersistenceError
from backend.models.calendar import (
    CalendarEvent,
    CalendarEventCursor,
    CalendarEventPage,
    CalendarEventStatus,
    CalendarEventTransparency,
    CalendarSyncWindow,
    StoredCalendarEvent,
)
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

    async def list_events(
        self,
        user_id: UUID,
        window: CalendarSyncWindow,
        limit: int,
        cursor: CalendarEventCursor | None,
    ) -> CalendarEventPage:
        parameters = {
            "select": (
                "id,user_id,provider_event_id,provider_calendar_id,title,description,"
                "location,start_time,end_time,is_all_day,status,transparency,"
                "provider_updated_at"
            ),
            "user_id": f"eq.{user_id}",
            "status": "neq.cancelled",
            "start_time": f"lt.{window.end_time.isoformat()}",
            "end_time": f"gt.{window.start_time.isoformat()}",
            "order": "start_time.asc,id.asc",
            "limit": str(limit + 1),
        }
        if cursor is not None:
            cursor_time = cursor.start_time.isoformat()
            parameters["or"] = (
                f"(start_time.gt.{cursor_time},"
                f"and(start_time.eq.{cursor_time},id.gt.{cursor.event_id}))"
            )
        try:
            response = await self._http_client.get(
                self._events_url,
                params=parameters,
                headers={"apikey": self._headers["apikey"]},
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as error:
            raise CalendarPersistenceError("Calendar events could not be loaded") from error
        if response.status_code >= 400:
            raise CalendarPersistenceError("Calendar events could not be loaded")
        try:
            payload: object = response.json()
            if not isinstance(payload, list):
                raise TypeError("Invalid calendar event collection")
            parsed_items = tuple(self._parse_stored_event(row) for row in payload)
        except (KeyError, TypeError, ValueError) as error:
            raise CalendarPersistenceError("Stored calendar events are invalid") from error
        page_items = parsed_items[:limit]
        next_cursor = None
        if len(parsed_items) > limit and page_items:
            last_item = page_items[-1]
            next_cursor = CalendarEventCursor(
                start_time=last_item.event.start_time,
                event_id=last_item.id,
            )
        return CalendarEventPage(items=page_items, next_cursor=next_cursor)

    async def mark_events_cancelled(
        self,
        user_id: UUID,
        provider_calendar_id: str,
        provider_event_ids: Sequence[str],
    ) -> None:
        if not provider_event_ids:
            return
        changed_at = datetime.now(UTC).isoformat()
        for start in range(0, len(provider_event_ids), 100):
            event_ids = provider_event_ids[start : start + 100]
            in_filter = f"in.({','.join(json.dumps(event_id) for event_id in event_ids)})"
            try:
                response = await self._http_client.patch(
                    self._events_url,
                    params={
                        "user_id": f"eq.{user_id}",
                        "provider_calendar_id": f"eq.{provider_calendar_id}",
                        "provider_event_id": in_filter,
                    },
                    headers=self._headers,
                    json={
                        "status": "cancelled",
                        "synced_at": changed_at,
                        "updated_at": changed_at,
                    },
                )
            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.ProtocolError,
            ) as error:
                raise CalendarPersistenceError(
                    "Cancelled calendar events could not be saved"
                ) from error
            if response.status_code >= 400:
                raise CalendarPersistenceError("Cancelled calendar events could not be saved")

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

    @staticmethod
    def _parse_stored_event(row: object) -> StoredCalendarEvent:
        if not isinstance(row, dict):
            raise TypeError("Invalid calendar event row")
        description = row.get("description")
        location = row.get("location")
        if description is not None and not isinstance(description, str):
            raise TypeError("Invalid calendar event description")
        if location is not None and not isinstance(location, str):
            raise TypeError("Invalid calendar event location")
        is_all_day = row["is_all_day"]
        if not isinstance(is_all_day, bool):
            raise TypeError("Invalid all-day marker")
        return StoredCalendarEvent(
            id=UUID(SupabaseCalendarRepository._required_string(row, "id")),
            event=CalendarEvent(
                user_id=UUID(SupabaseCalendarRepository._required_string(row, "user_id")),
                provider_event_id=SupabaseCalendarRepository._required_string(
                    row, "provider_event_id"
                ),
                provider_calendar_id=SupabaseCalendarRepository._required_string(
                    row, "provider_calendar_id"
                ),
                title=SupabaseCalendarRepository._required_string(row, "title"),
                description=description,
                location=location,
                start_time=datetime.fromisoformat(
                    SupabaseCalendarRepository._required_string(row, "start_time")
                ),
                end_time=datetime.fromisoformat(
                    SupabaseCalendarRepository._required_string(row, "end_time")
                ),
                is_all_day=is_all_day,
                status=CalendarEventStatus(
                    SupabaseCalendarRepository._required_string(row, "status")
                ),
                transparency=CalendarEventTransparency(
                    SupabaseCalendarRepository._required_string(row, "transparency")
                ),
                provider_updated_at=datetime.fromisoformat(
                    SupabaseCalendarRepository._required_string(row, "provider_updated_at")
                ),
            ),
        )

    @staticmethod
    def _required_string(row: dict[str, object], field: str) -> str:
        value = row.get(field)
        if not isinstance(value, str) or not value:
            raise TypeError("Invalid stored calendar event")
        return value
