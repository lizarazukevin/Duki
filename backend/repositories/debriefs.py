from typing import Protocol
from uuid import UUID

from backend.models.debriefs import DailyDebrief, DailyDebriefDraft


class DebriefRepository(Protocol):
    """Persistence port for one atomic evening debrief reconciliation."""

    async def reconcile_debrief(
        self,
        user_id: UUID,
        draft: DailyDebriefDraft,
        morning_mood_score: float,
        completed_task_count: int,
    ) -> DailyDebrief: ...
