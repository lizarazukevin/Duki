from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from backend.models.task_events import TaskCompletionFeedback, TaskCompletionResult
from backend.models.tasks import TaskStatus


class TaskCompletionRequest(BaseModel):
    actual_minutes: int = Field(gt=0)
    actual_easiness_score: int = Field(ge=1, le=5)

    def to_domain(self) -> TaskCompletionFeedback:
        return TaskCompletionFeedback(
            actual_minutes=self.actual_minutes,
            actual_easiness_score=self.actual_easiness_score,
        )


class TaskCompletionResponse(BaseModel):
    event_id: UUID
    task_id: UUID
    status: TaskStatus
    completed_at: datetime
    actual_minutes: int
    actual_easiness_score: int
    estimated_minutes_snapshot: int | None
    initial_easiness_score_snapshot: int | None
    estimate_delta_minutes: int | None
    easiness_delta: int | None

    @classmethod
    def from_domain(cls, result: TaskCompletionResult) -> Self:
        completed_at = result.task.completed_at
        if completed_at is None:
            raise ValueError("Completed task is missing its completion timestamp")
        metrics = result.event.metrics
        return cls(
            event_id=result.event.id,
            task_id=result.task.id,
            status=result.task.status,
            completed_at=completed_at,
            actual_minutes=metrics.actual_minutes,
            actual_easiness_score=metrics.actual_easiness_score,
            estimated_minutes_snapshot=metrics.estimated_minutes_snapshot,
            initial_easiness_score_snapshot=metrics.initial_easiness_score_snapshot,
            estimate_delta_minutes=metrics.estimate_delta_minutes,
            easiness_delta=metrics.easiness_delta,
        )
