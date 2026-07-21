import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from backend.errors import InvalidPaginationCursorError
from backend.models.calendar import (
    CalendarEventCursor,
    CalendarEventListResult,
    CalendarSyncWindow,
)
from backend.repositories.calendar import CalendarRepository

MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100


class CalendarQueryService:
    """Read a user's cached calendar with stable opaque cursor pagination."""

    def __init__(self, calendar_repository: CalendarRepository) -> None:
        self._calendar_repository = calendar_repository

    async def list_events(
        self,
        user_id: UUID,
        window: CalendarSyncWindow,
        limit: int,
        encoded_cursor: str | None,
    ) -> CalendarEventListResult:
        if not MIN_PAGE_SIZE <= limit <= MAX_PAGE_SIZE:
            raise ValueError("Calendar page size must be between 1 and 100")
        cursor = self._decode_cursor(encoded_cursor) if encoded_cursor else None
        page = await self._calendar_repository.list_events(
            user_id=user_id,
            window=window,
            limit=limit,
            cursor=cursor,
        )
        return CalendarEventListResult(
            items=page.items,
            next_cursor=(
                self._encode_cursor(page.next_cursor) if page.next_cursor is not None else None
            ),
        )

    @staticmethod
    def _encode_cursor(cursor: CalendarEventCursor) -> str:
        payload = json.dumps(
            [cursor.start_time.isoformat(), str(cursor.event_id)],
            separators=(",", ":"),
        ).encode("utf-8")
        return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode_cursor(encoded_cursor: str) -> CalendarEventCursor:
        try:
            padding = "=" * (-len(encoded_cursor) % 4)
            decoded = base64.b64decode(
                f"{encoded_cursor}{padding}",
                altchars=b"-_",
                validate=True,
            )
            payload: object = json.loads(decoded.decode("utf-8"))
            if not isinstance(payload, list) or len(payload) != 2:
                raise TypeError("Invalid cursor payload")
            start_time, event_id = payload
            if not isinstance(start_time, str) or not isinstance(event_id, str):
                raise TypeError("Invalid cursor fields")
            parsed_start_time = datetime.fromisoformat(start_time)
            if parsed_start_time.utcoffset() is None:
                raise ValueError("Cursor timestamp has no timezone")
            return CalendarEventCursor(
                start_time=parsed_start_time,
                event_id=UUID(event_id),
            )
        except (
            binascii.Error,
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:
            raise InvalidPaginationCursorError("The calendar cursor is invalid") from error
