from datetime import date
from typing import Protocol
from uuid import UUID

from backend.models.moods import DailyMood


class MoodRepository(Protocol):
    """Persistence port for private daily mood records."""

    async def upsert_mood(self, mood: DailyMood) -> None: ...

    async def get_mood(self, user_id: UUID, mood_date: date) -> DailyMood: ...
