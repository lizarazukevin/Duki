from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.models.duck_sessions import (
    DuckSession,
    DuckSessionStatus,
    SuggestedTaskAction,
    TaskResolutionDecision,
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


class TaskResolutionDecisionResponse(BaseModel):
    task_id: UUID
    action: SuggestedTaskAction
    actual_minutes: int | None
    actual_easiness_score: int | None

    @classmethod
    def from_domain(cls, decision: TaskResolutionDecision) -> Self:
        return cls.model_validate(decision, from_attributes=True)


class DuckSessionResponse(BaseModel):
    id: UUID
    status: DuckSessionStatus
    transcript: str | None
    root_task_id: UUID | None
    resolution_suggestions: list[TaskResolutionSuggestionResponse]
    confirmed_resolutions: list[TaskResolutionDecisionResponse]
    confirmed_at: datetime | None
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
            confirmed_resolutions=[
                TaskResolutionDecisionResponse.from_domain(decision)
                for decision in session.confirmed_resolutions
            ],
            confirmed_at=session.confirmed_at,
            failure_code=session.failure_code,
            finished_at=session.finished_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )


class TaskResolutionDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    action: SuggestedTaskAction
    actual_minutes: int | None = Field(default=None, gt=0)
    actual_easiness_score: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def validate_domain_rules(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> TaskResolutionDecision:
        return TaskResolutionDecision(
            self.task_id,
            self.action,
            self.actual_minutes,
            self.actual_easiness_score,
        )


class DuckSessionConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: list[TaskResolutionDecisionRequest] = Field(min_length=1, max_length=100)
