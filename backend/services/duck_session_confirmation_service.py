from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from backend.errors import DuckSessionConfirmationConflictError
from backend.models.duck_sessions import (
    DuckSession,
    DuckSessionStatus,
    TaskResolutionDecision,
)
from backend.repositories.duck_sessions import DuckSessionRepository


class DuckSessionConfirmationService:
    """Apply a user's final decisions for every suggested task resolution."""

    def __init__(self, session_repository: DuckSessionRepository) -> None:
        self._session_repository = session_repository

    async def confirm(
        self,
        user_id: UUID,
        session_id: UUID,
        decisions: tuple[TaskResolutionDecision, ...],
    ) -> DuckSession:
        session = await self._session_repository.get_session(user_id, session_id)
        if session.status is not DuckSessionStatus.COMPLETED or session.confirmed_at is not None:
            raise DuckSessionConfirmationConflictError(
                "Duck session cannot be confirmed from its current state"
            )
        suggested_ids = {suggestion.task_id for suggestion in session.resolution_suggestions}
        decision_ids = [decision.task_id for decision in decisions]
        if len(decision_ids) != len(set(decision_ids)) or set(decision_ids) != suggested_ids:
            raise DuckSessionConfirmationConflictError(
                "Every suggested task requires exactly one decision"
            )

        confirmed_at = datetime.now(UTC)
        await self._session_repository.confirm_session(
            user_id,
            session_id,
            decisions,
            confirmed_at,
        )
        return replace(
            session,
            confirmed_resolutions=decisions,
            confirmed_at=confirmed_at,
            updated_at=confirmed_at,
        )
