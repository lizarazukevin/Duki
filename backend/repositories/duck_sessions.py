from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.models.duck_sessions import DuckSession, TaskResolutionDecision
from backend.models.tasks import Task


class DuckSessionRepository(Protocol):
    """Persistence port for private voice-to-task session state."""

    async def create_session(self, session: DuckSession) -> None: ...

    async def update_session(self, session: DuckSession) -> None: ...

    async def complete_session(
        self,
        session: DuckSession,
        tasks: Sequence[Task],
    ) -> None: ...

    async def get_session(self, user_id: UUID, session_id: UUID) -> DuckSession: ...

    async def confirm_session(
        self,
        user_id: UUID,
        session_id: UUID,
        decisions: Sequence[TaskResolutionDecision],
        confirmed_at: datetime,
    ) -> None: ...
