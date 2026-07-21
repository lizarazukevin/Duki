from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from backend.models.calendar import (
    CalendarEventStatus,
    CalendarEventTransparency,
    CalendarFreeBlock,
    CalendarSyncWindow,
    StoredCalendarEvent,
)


class CalendarSyncRequest(BaseModel):
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        CalendarSyncWindow(start_time=self.start_time, end_time=self.end_time)
        return self

    def to_domain(self) -> CalendarSyncWindow:
        return CalendarSyncWindow(start_time=self.start_time, end_time=self.end_time)


class CalendarSyncResponse(BaseModel):
    events_upserted: int
    events_cancelled: int


class CalendarEventListQuery(BaseModel):
    start_time: datetime
    end_time: datetime
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        CalendarSyncWindow(start_time=self.start_time, end_time=self.end_time)
        return self

    def to_window(self) -> CalendarSyncWindow:
        return CalendarSyncWindow(start_time=self.start_time, end_time=self.end_time)


class CalendarEventResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    location: str | None
    start_time: datetime
    end_time: datetime
    is_all_day: bool
    status: CalendarEventStatus
    transparency: CalendarEventTransparency

    @classmethod
    def from_domain(cls, stored_event: StoredCalendarEvent) -> Self:
        event = stored_event.event
        return cls(
            id=stored_event.id,
            title=event.title,
            description=event.description,
            location=event.location,
            start_time=event.start_time,
            end_time=event.end_time,
            is_all_day=event.is_all_day,
            status=event.status,
            transparency=event.transparency,
        )


class CalendarEventListResponse(BaseModel):
    items: list[CalendarEventResponse]
    next_cursor: str | None


class CalendarFreeBlockQuery(BaseModel):
    start_time: datetime
    end_time: datetime
    minimum_minutes: int = Field(default=15, ge=1, le=480)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        CalendarSyncWindow(start_time=self.start_time, end_time=self.end_time)
        return self

    def to_window(self) -> CalendarSyncWindow:
        return CalendarSyncWindow(start_time=self.start_time, end_time=self.end_time)


class CalendarFreeBlockResponse(BaseModel):
    start_time: datetime
    end_time: datetime
    duration_minutes: int

    @classmethod
    def from_domain(cls, block: CalendarFreeBlock) -> Self:
        return cls(
            start_time=block.start_time,
            end_time=block.end_time,
            duration_minutes=block.duration_minutes,
        )


class CalendarFreeBlockListResponse(BaseModel):
    items: list[CalendarFreeBlockResponse]
