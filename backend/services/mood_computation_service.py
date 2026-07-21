from collections.abc import Sequence
from datetime import datetime, time, timedelta

from backend.models.calendar import (
    CalendarEvent,
    CalendarEventStatus,
    CalendarEventTransparency,
)
from backend.models.moods import MoodComputation

STANDARD_WORKDAY_MINUTES = 8 * 60
EARLY_START_HOUR = 9
EARLY_START_WINDOW_MINUTES = 2 * 60
BACK_TO_BACK_GAP = timedelta(minutes=10)
MEETING_DENSITY_WEIGHT = 0.55
BACK_TO_BACK_WEIGHT = 0.30
EARLY_START_WEIGHT = 0.15
MAX_CALENDAR_MOOD_PENALTY = 1.5


class MoodComputationService:
    """Compute an auditable mood adjustment from the user's cached calendar shape."""

    def compute(
        self,
        reported_mood_score: int,
        events: Sequence[CalendarEvent],
        day_start: datetime,
        day_end: datetime,
    ) -> MoodComputation:
        if (
            not isinstance(reported_mood_score, int)
            or isinstance(reported_mood_score, bool)
            or not 1 <= reported_mood_score <= 5
        ):
            raise ValueError("Reported mood score must be between 1 and 5")
        if day_start.utcoffset() is None or day_end.utcoffset() is None:
            raise ValueError("Mood day boundaries must include a timezone")
        if day_end <= day_start:
            raise ValueError("Mood day end must be after its start")

        busy_intervals = self._busy_intervals(events, day_start, day_end)
        meeting_density = min(
            self._busy_minutes(busy_intervals) / STANDARD_WORKDAY_MINUTES,
            1.0,
        )
        back_to_back_load = self._back_to_back_load(busy_intervals)
        early_start_load = self._early_start_load(busy_intervals, day_start)
        calendar_load = round(
            meeting_density * MEETING_DENSITY_WEIGHT
            + back_to_back_load * BACK_TO_BACK_WEIGHT
            + early_start_load * EARLY_START_WEIGHT,
            3,
        )
        computed_mood = round(
            max(1.0, reported_mood_score - calendar_load * MAX_CALENDAR_MOOD_PENALTY),
            3,
        )
        return MoodComputation(
            calendar_load_score=calendar_load,
            computed_mood_score=computed_mood,
        )

    @staticmethod
    def _busy_intervals(
        events: Sequence[CalendarEvent],
        day_start: datetime,
        day_end: datetime,
    ) -> tuple[tuple[datetime, datetime], ...]:
        intervals = sorted(
            (
                (max(event.start_time, day_start), min(event.end_time, day_end))
                for event in events
                if not event.is_all_day
                and event.status is not CalendarEventStatus.CANCELLED
                and event.transparency is CalendarEventTransparency.OPAQUE
                and event.end_time > day_start
                and event.start_time < day_end
            ),
            key=lambda interval: interval[0],
        )
        return tuple(interval for interval in intervals if interval[1] > interval[0])

    @staticmethod
    def _busy_minutes(intervals: Sequence[tuple[datetime, datetime]]) -> float:
        if not intervals:
            return 0.0
        merged: list[tuple[datetime, datetime]] = [intervals[0]]
        for start_time, end_time in intervals[1:]:
            previous_start, previous_end = merged[-1]
            if start_time <= previous_end:
                merged[-1] = (previous_start, max(previous_end, end_time))
            else:
                merged.append((start_time, end_time))
        return sum((end - start).total_seconds() / 60 for start, end in merged)

    @staticmethod
    def _back_to_back_load(intervals: Sequence[tuple[datetime, datetime]]) -> float:
        if len(intervals) < 2:
            return 0.0
        back_to_back_pairs = sum(
            current_start - previous_end <= BACK_TO_BACK_GAP
            for (_, previous_end), (current_start, _) in zip(
                intervals,
                intervals[1:],
                strict=False,
            )
        )
        return back_to_back_pairs / (len(intervals) - 1)

    @staticmethod
    def _early_start_load(
        intervals: Sequence[tuple[datetime, datetime]],
        day_start: datetime,
    ) -> float:
        if not intervals:
            return 0.0
        early_start_boundary = datetime.combine(
            day_start.date(),
            time(EARLY_START_HOUR),
            tzinfo=day_start.tzinfo,
        )
        minutes_early = max(
            0.0,
            (early_start_boundary - intervals[0][0]).total_seconds() / 60,
        )
        return min(minutes_early / EARLY_START_WINDOW_MINUTES, 1.0)
