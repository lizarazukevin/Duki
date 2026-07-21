from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.models.auth import GoogleCredentials


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
