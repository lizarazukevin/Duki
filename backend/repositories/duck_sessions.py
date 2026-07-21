from typing import Protocol
from uuid import UUID

from backend.models.duck_sessions import DuckSession


class DuckSessionRepository(Protocol):
    """Persistence port for private voice-to-task session state."""

    async def create_session(self, session: DuckSession) -> None: ...

    async def update_session(self, session: DuckSession) -> None: ...

    async def get_session(self, user_id: UUID, session_id: UUID) -> DuckSession: ...
