from datetime import date
from typing import Protocol
from uuid import UUID

from backend.models.moods import DailyMood, MoodComputation, MoodPoll


class MoodRepository(Protocol):
    """Persistence port for private daily mood records."""

    async def upsert_mood(
        self,
        user_id: UUID,
        poll: MoodPoll,
        computation: MoodComputation,
    ) -> DailyMood: ...

    async def get_mood(self, user_id: UUID, mood_date: date) -> DailyMood: ...
