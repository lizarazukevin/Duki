from datetime import date, datetime, time, timedelta
from typing import Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from backend.models.moods import DailyMood, MoodPoll


class MoodPollRequest(BaseModel):
    mood_date: date
    reported_mood_score: int = Field(ge=1, le=5)
    timezone: str = Field(min_length=1, max_length=100)

    @field_validator("timezone")
    @classmethod
    def timezone_must_be_supported(cls, timezone_name: str) -> str:
        try:
            ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("Timezone must be a supported IANA timezone") from error
        return timezone_name

    def to_domain(self) -> MoodPoll:
        return MoodPoll(
            mood_date=self.mood_date,
            reported_mood_score=self.reported_mood_score,
        )

    def day_boundaries(self) -> tuple[datetime, datetime]:
        timezone = ZoneInfo(self.timezone)
        day_start = datetime.combine(self.mood_date, time.min, tzinfo=timezone)
        day_end = datetime.combine(
            self.mood_date + timedelta(days=1),
            time.min,
            tzinfo=timezone,
        )
        return day_start, day_end


class DailyMoodResponse(BaseModel):
    id: UUID
    mood_date: date
    reported_mood_score: int
    calendar_load_score: float
    computed_mood_score: float
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, mood: DailyMood) -> Self:
        return cls(
            id=mood.id,
            mood_date=mood.mood_date,
            reported_mood_score=mood.reported_mood_score,
            calendar_load_score=mood.calendar_load_score,
            computed_mood_score=mood.computed_mood_score,
            created_at=mood.created_at,
            updated_at=mood.updated_at,
        )
