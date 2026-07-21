from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MoodPoll:
    mood_date: date
    reported_mood_score: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.reported_mood_score, int)
            or isinstance(self.reported_mood_score, bool)
            or not 1 <= self.reported_mood_score <= 5
        ):
            raise ValueError("Reported mood score must be between 1 and 5")


@dataclass(frozen=True, slots=True)
class MoodComputation:
    calendar_load_score: float
    computed_mood_score: float

    def __post_init__(self) -> None:
        if not 0 <= self.calendar_load_score <= 1:
            raise ValueError("Calendar load score must be between 0 and 1")
        if not 1 <= self.computed_mood_score <= 5:
            raise ValueError("Computed mood score must be between 1 and 5")


@dataclass(frozen=True, slots=True)
class DailyMood:
    id: UUID
    user_id: UUID
    mood_date: date
    reported_mood_score: int
    calendar_load_score: float
    computed_mood_score: float
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        MoodPoll(self.mood_date, self.reported_mood_score)
        MoodComputation(self.calendar_load_score, self.computed_mood_score)
        if self.created_at.utcoffset() is None or self.updated_at.utcoffset() is None:
            raise ValueError("Daily mood timestamps must include a timezone")
