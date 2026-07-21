import logging
from datetime import date, datetime
from uuid import UUID

from backend.errors import CalendarPersistenceError
from backend.models.calendar import CalendarEvent, CalendarSyncWindow
from backend.models.moods import DailyMood, MoodPoll
from backend.repositories.calendar import CalendarRepository
from backend.repositories.moods import MoodRepository
from backend.services.mood_computation_service import MoodComputationService

logger = logging.getLogger(__name__)

CALENDAR_PAGE_SIZE = 100


class MoodService:
    """Record a daily poll after deriving load from cached calendar events."""

    def __init__(
        self,
        mood_repository: MoodRepository,
        calendar_repository: CalendarRepository,
        computation_service: MoodComputationService,
    ) -> None:
        self._mood_repository = mood_repository
        self._calendar_repository = calendar_repository
        self._computation_service = computation_service

    async def record_mood(
        self,
        user_id: UUID,
        poll: MoodPoll,
        day_start: datetime,
        day_end: datetime,
    ) -> DailyMood:
        if day_start.date() != poll.mood_date:
            raise ValueError("Mood date must match the local day boundary")

        events = await self._load_calendar_events(user_id, day_start, day_end)
        computation = self._computation_service.compute(
            poll.reported_mood_score,
            events,
            day_start,
            day_end,
        )
        return await self._mood_repository.upsert_mood(user_id, poll, computation)

    async def get_mood(self, user_id: UUID, mood_date: date) -> DailyMood:
        return await self._mood_repository.get_mood(user_id, mood_date)

    async def _load_calendar_events(
        self,
        user_id: UUID,
        day_start: datetime,
        day_end: datetime,
    ) -> tuple[CalendarEvent, ...]:
        window = CalendarSyncWindow(day_start, day_end)
        events: list[CalendarEvent] = []
        cursor = None
        try:
            while True:
                page = await self._calendar_repository.list_events(
                    user_id,
                    window,
                    CALENDAR_PAGE_SIZE,
                    cursor,
                )
                events.extend(item.event for item in page.items)
                if page.next_cursor is None:
                    return tuple(events)
                cursor = page.next_cursor
        except CalendarPersistenceError:
            logger.warning("mood_calendar_load_unavailable user_id=%s", user_id)
            return ()
