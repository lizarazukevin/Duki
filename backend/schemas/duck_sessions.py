from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from backend.models.duck_sessions import (
    DuckSession,
    DuckSessionStatus,
    SuggestedTaskAction,
    TaskResolutionSuggestion,
)


class TaskResolutionSuggestionResponse(BaseModel):
    task_id: UUID
    suggested_action: SuggestedTaskAction
    actual_minutes: int | None
    actual_easiness_score: int | None

    @classmethod
    def from_domain(cls, suggestion: TaskResolutionSuggestion) -> Self:
        return cls.model_validate(suggestion, from_attributes=True)


class DuckSessionResponse(BaseModel):
    id: UUID
    status: DuckSessionStatus
    transcript: str | None
    root_task_id: UUID | None
    resolution_suggestions: list[TaskResolutionSuggestionResponse]
    failure_code: str | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, session: DuckSession) -> Self:
        return cls(
            id=session.id,
            status=session.status,
            transcript=session.transcript,
            root_task_id=session.root_task_id,
            resolution_suggestions=[
                TaskResolutionSuggestionResponse.from_domain(suggestion)
                for suggestion in session.resolution_suggestions
            ],
            failure_code=session.failure_code,
            finished_at=session.finished_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
