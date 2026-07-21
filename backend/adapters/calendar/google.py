from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from urllib.parse import quote
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from backend.adapters.calendar.base import CalendarAdapter
from backend.constants import PRIMARY_CALENDAR_ID
from backend.errors import (
    CalendarAuthorizationError,
    CalendarRateLimitError,
    CalendarUnavailableError,
)
from backend.models.auth import GoogleCredentials
from backend.models.calendar import (
    CalendarEvent,
    CalendarEventStatus,
    CalendarEventTransparency,
    CalendarFetchResult,
)

GOOGLE_CALENDAR_API_URL = "https://www.googleapis.com/calendar/v3"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_EVENT_TITLE = "Busy"
TOKEN_EXPIRY_SKEW = timedelta(minutes=1)
RATE_LIMIT_REASONS = frozenset({"rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded"})


class GoogleCalendarAdapter(CalendarAdapter):
    """Refresh Google access and normalize fully paginated Calendar events."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._http_client = http_client
        self._client_id = client_id
        self._client_secret = client_secret

    async def list_events(
        self,
        credentials: GoogleCredentials,
        start_time: datetime,
        end_time: datetime,
        calendar_id: str = PRIMARY_CALENDAR_ID,
    ) -> CalendarFetchResult:
        active_credentials = credentials
        refreshed_credentials: GoogleCredentials | None = None
        if self._needs_refresh(credentials):
            active_credentials = await self._refresh_credentials(credentials)
            refreshed_credentials = active_credentials

        events: list[CalendarEvent] = []
        cancelled_event_ids: list[str] = []
        page_token: str | None = None
        seen_page_tokens: set[str] = set()
        while True:
            payload = await self._fetch_page(
                access_token=active_credentials.access_token,
                calendar_id=calendar_id,
                start_time=start_time,
                end_time=end_time,
                page_token=page_token,
            )
            calendar_timezone = self._parse_timezone(payload.get("timeZone"))
            items = payload.get("items", [])
            if not isinstance(items, list):
                raise CalendarUnavailableError("Google Calendar returned invalid events")
            for item in items:
                if not isinstance(item, dict):
                    raise CalendarUnavailableError("Google Calendar returned an invalid event")
                event_id = self._required_string(item, "id")
                if item.get("status") == CalendarEventStatus.CANCELLED.value:
                    cancelled_event_ids.append(event_id)
                    continue
                events.append(
                    self._parse_event(
                        item=item,
                        user_id=credentials.user_id,
                        calendar_id=calendar_id,
                        calendar_timezone=calendar_timezone,
                    )
                )
            next_page_token = payload.get("nextPageToken")
            if next_page_token is None:
                break
            if not isinstance(next_page_token, str) or not next_page_token:
                raise CalendarUnavailableError("Google Calendar returned invalid pagination")
            if next_page_token in seen_page_tokens:
                raise CalendarUnavailableError("Google Calendar pagination repeated")
            seen_page_tokens.add(next_page_token)
            page_token = next_page_token

        return CalendarFetchResult(
            events=tuple(events),
            cancelled_event_ids=tuple(cancelled_event_ids),
            refreshed_credentials=refreshed_credentials,
        )

    @staticmethod
    def _needs_refresh(credentials: GoogleCredentials) -> bool:
        expires_at = credentials.access_token_expires_at
        return expires_at is None or expires_at <= datetime.now(UTC) + TOKEN_EXPIRY_SKEW

    async def _refresh_credentials(
        self,
        credentials: GoogleCredentials,
    ) -> GoogleCredentials:
        try:
            response = await self._http_client.post(
                GOOGLE_OAUTH_TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": credentials.refresh_token,
                },
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as error:
            raise CalendarUnavailableError("Google token refresh is unavailable") from error
        if response.status_code in {400, 401, 403}:
            raise CalendarAuthorizationError("Google Calendar must be reconnected")
        if response.status_code == 429:
            raise CalendarRateLimitError("Google token refresh rate limit reached")
        if response.status_code >= 500:
            raise CalendarUnavailableError("Google token refresh is temporarily unavailable")
        if response.status_code >= 400:
            raise CalendarUnavailableError("Google token refresh failed")
        try:
            payload: object = response.json()
            if not isinstance(payload, dict):
                raise TypeError("Invalid refresh payload")
            access_token = payload["access_token"]
            expires_in = payload["expires_in"]
            if not isinstance(access_token, str) or not access_token:
                raise TypeError("Invalid access token")
            if not isinstance(expires_in, int) or expires_in <= 0:
                raise TypeError("Invalid token expiry")
        except (KeyError, TypeError, ValueError) as error:
            raise CalendarUnavailableError("Google returned an invalid token") from error
        return GoogleCredentials(
            user_id=credentials.user_id,
            access_token=access_token,
            refresh_token=credentials.refresh_token,
            access_token_expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )

    async def _fetch_page(
        self,
        access_token: str,
        calendar_id: str,
        start_time: datetime,
        end_time: datetime,
        page_token: str | None,
    ) -> dict[str, Any]:
        parameters = {
            "timeMin": start_time.isoformat(),
            "timeMax": end_time.isoformat(),
            "singleEvents": "true",
            "showDeleted": "true",
            "orderBy": "startTime",
            "maxResults": "2500",
        }
        if page_token is not None:
            parameters["pageToken"] = page_token
        try:
            response = await self._http_client.get(
                f"{GOOGLE_CALENDAR_API_URL}/calendars/{quote(calendar_id, safe='')}/events",
                params=parameters,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as error:
            raise CalendarUnavailableError("Google Calendar is temporarily unavailable") from error
        self._raise_for_calendar_error(response)
        try:
            payload: object = response.json()
            if not isinstance(payload, dict):
                raise TypeError("Invalid calendar payload")
            return payload
        except (TypeError, ValueError) as error:
            raise CalendarUnavailableError("Google Calendar returned invalid data") from error

    @staticmethod
    def _raise_for_calendar_error(response: httpx.Response) -> None:
        if response.status_code == 401:
            raise CalendarAuthorizationError("Google Calendar must be reconnected")
        reasons = GoogleCalendarAdapter._error_reasons(response)
        if response.status_code == 429 or reasons.intersection(RATE_LIMIT_REASONS):
            raise CalendarRateLimitError("Google Calendar rate limit reached")
        if response.status_code == 403:
            raise CalendarAuthorizationError("Google Calendar access was denied")
        if response.status_code >= 400:
            raise CalendarUnavailableError("Google Calendar request failed")

    @staticmethod
    def _error_reasons(response: httpx.Response) -> set[str]:
        try:
            payload: object = response.json()
            if not isinstance(payload, dict):
                return set()
            error = payload.get("error")
            if not isinstance(error, dict):
                return set()
            errors = error.get("errors", [])
            if not isinstance(errors, list):
                return set()
            return {
                reason
                for item in errors
                if isinstance(item, dict) and isinstance((reason := item.get("reason")), str)
            }
        except ValueError:
            return set()

    @staticmethod
    def _parse_event(
        item: dict[str, Any],
        user_id: UUID,
        calendar_id: str,
        calendar_timezone: ZoneInfo,
    ) -> CalendarEvent:
        start = GoogleCalendarAdapter._required_dict(item, "start")
        end = GoogleCalendarAdapter._required_dict(item, "end")
        start_time, is_all_day = GoogleCalendarAdapter._parse_event_time(start, calendar_timezone)
        end_time, end_is_all_day = GoogleCalendarAdapter._parse_event_time(end, calendar_timezone)
        if is_all_day != end_is_all_day or end_time <= start_time:
            raise CalendarUnavailableError("Google Calendar returned invalid event times")
        try:
            status = CalendarEventStatus(item.get("status", "confirmed"))
            transparency = CalendarEventTransparency(item.get("transparency", "opaque"))
            provider_updated_at = GoogleCalendarAdapter._parse_datetime(
                GoogleCalendarAdapter._required_string(item, "updated")
            )
        except (TypeError, ValueError) as error:
            raise CalendarUnavailableError("Google Calendar returned an invalid event") from error
        return CalendarEvent(
            user_id=user_id,
            provider_event_id=GoogleCalendarAdapter._required_string(item, "id"),
            provider_calendar_id=calendar_id,
            title=GoogleCalendarAdapter._optional_string(item.get("summary"))
            or DEFAULT_EVENT_TITLE,
            description=GoogleCalendarAdapter._optional_string(item.get("description")),
            location=GoogleCalendarAdapter._optional_string(item.get("location")),
            start_time=start_time,
            end_time=end_time,
            is_all_day=is_all_day,
            status=status,
            transparency=transparency,
            provider_updated_at=provider_updated_at,
        )

    @staticmethod
    def _parse_event_time(value: dict[str, Any], timezone: ZoneInfo) -> tuple[datetime, bool]:
        date_time = value.get("dateTime")
        if isinstance(date_time, str):
            return GoogleCalendarAdapter._parse_datetime(date_time), False
        date_value = value.get("date")
        if isinstance(date_value, str):
            try:
                parsed_date = date.fromisoformat(date_value)
            except ValueError as error:
                raise CalendarUnavailableError(
                    "Google Calendar returned an invalid all-day event"
                ) from error
            return datetime.combine(parsed_date, time.min, timezone), True
        raise CalendarUnavailableError("Google Calendar event time is missing")

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Calendar timestamp has no timezone")
        return parsed

    @staticmethod
    def _parse_timezone(value: object) -> ZoneInfo:
        if not isinstance(value, str):
            return ZoneInfo("UTC")
        try:
            return ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise CalendarUnavailableError(
                "Google Calendar returned an invalid timezone"
            ) from error

    @staticmethod
    def _required_dict(payload: dict[str, Any], field: str) -> dict[str, Any]:
        value = payload.get(field)
        if not isinstance(value, dict):
            raise CalendarUnavailableError("Google Calendar event is incomplete")
        return value

    @staticmethod
    def _required_string(payload: dict[str, Any], field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            raise CalendarUnavailableError("Google Calendar event is incomplete")
        return value

    @staticmethod
    def _optional_string(value: object) -> str | None:
        return value if isinstance(value, str) else None
