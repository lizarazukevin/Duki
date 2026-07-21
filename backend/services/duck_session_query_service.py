from uuid import UUID

from backend.models.duck_sessions import DuckSession
from backend.repositories.duck_sessions import DuckSessionRepository


class DuckSessionQueryService:
    """Load private duck-session results independently of processing providers."""

    def __init__(self, session_repository: DuckSessionRepository) -> None:
        self._session_repository = session_repository

    async def get_session(self, user_id: UUID, session_id: UUID) -> DuckSession:
        return await self._session_repository.get_session(user_id, session_id)
