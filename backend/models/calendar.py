from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from backend.models.auth import GoogleCredentials

MAX_CALENDAR_SYNC_RANGE = timedelta(days=366)


class CalendarEventStatus(StrEnum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class CalendarEventTransparency(StrEnum):
    OPAQUE = "opaque"
    TRANSPARENT = "transparent"


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """A provider-neutral calendar event ready for local persistence."""

    user_id: UUID
    provider_event_id: str
    provider_calendar_id: str
    title: str
    description: str | None
    location: str | None
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    status: CalendarEventStatus
    transparency: CalendarEventTransparency
    provider_updated_at: datetime


@dataclass(frozen=True, slots=True)
class CalendarFetchResult:
    """Normalized changes from one complete provider pagination cycle."""

    events: tuple[CalendarEvent, ...]
    cancelled_event_ids: tuple[str, ...]
    refreshed_credentials: GoogleCredentials | None


@dataclass(frozen=True, slots=True)
class CalendarWriteResult:
    """One provider event write plus any refreshed credentials it produced."""

    event: CalendarEvent
    refreshed_credentials: GoogleCredentials | None


@dataclass(frozen=True, slots=True)
class TaskCalendarEventLink:
    """Stable relationship between a Duky task and its provider event."""

    user_id: UUID
    task_id: UUID
    provider_event_id: str
    provider_calendar_id: str
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True, slots=True)
class CalendarSyncWindow:
    start_time: datetime
    end_time: datetime

    def __post_init__(self) -> None:
        if self.start_time.utcoffset() is None or self.end_time.utcoffset() is None:
            raise ValueError("Calendar sync timestamps must include a timezone")
        if self.end_time <= self.start_time:
            raise ValueError("Calendar sync end time must be after its start time")
        if self.end_time - self.start_time > MAX_CALENDAR_SYNC_RANGE:
            raise ValueError("Calendar sync window cannot exceed 366 days")


@dataclass(frozen=True, slots=True)
class CalendarSyncSummary:
    events_upserted: int
    events_cancelled: int


@dataclass(frozen=True, slots=True)
class StoredCalendarEvent:
    id: UUID
    event: CalendarEvent


@dataclass(frozen=True, slots=True)
class CalendarEventCursor:
    start_time: datetime
    event_id: UUID


@dataclass(frozen=True, slots=True)
class CalendarEventPage:
    items: tuple[StoredCalendarEvent, ...]
    next_cursor: CalendarEventCursor | None


@dataclass(frozen=True, slots=True)
class CalendarEventListResult:
    items: tuple[StoredCalendarEvent, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class CalendarFreeBlock:
    start_time: datetime
    end_time: datetime

    def __post_init__(self) -> None:
        if self.start_time.utcoffset() is None or self.end_time.utcoffset() is None:
            raise ValueError("Free-block timestamps must include a timezone")
        if self.end_time <= self.start_time:
            raise ValueError("Free-block end time must be after its start time")

    @property
    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() // 60)
