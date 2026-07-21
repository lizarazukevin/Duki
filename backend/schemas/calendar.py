from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from backend.models.calendar import (
    CalendarEvent,
    CalendarEventStatus,
    CalendarEventTransparency,
    CalendarFreeBlock,
    CalendarSyncWindow,
    StoredCalendarEvent,
)


class TaskCalendarEventRequest(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("Start and end time must be supplied together")
        if self.start_time is not None and self.end_time is not None:
            CalendarSyncWindow(start_time=self.start_time, end_time=self.end_time)
        return self


class TaskCalendarEventResponse(BaseModel):
    task_id: UUID
    linked: bool
    provider_event_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    @classmethod
    def from_domain(
        cls,
        task_id: UUID,
        event: CalendarEvent | None,
    ) -> Self:
        return cls(
            task_id=task_id,
            linked=event is not None,
            provider_event_id=event.provider_event_id if event is not None else None,
            start_time=event.start_time if event is not None else None,
            end_time=event.end_time if event is not None else None,
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
