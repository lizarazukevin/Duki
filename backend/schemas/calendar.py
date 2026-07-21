from datetime import datetime
from typing import Self

from pydantic import BaseModel, model_validator

from backend.models.calendar import CalendarSyncWindow


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
