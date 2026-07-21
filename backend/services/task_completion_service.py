from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.errors import TaskCompletionConflictError
from backend.models.task_events import (
    TaskCompletionFeedback,
    TaskCompletionMetrics,
    TaskCompletionResult,
    TaskEvent,
    TaskEventType,
)
from backend.models.tasks import Task, TaskStatus
from backend.repositories.task_events import TaskCompletionRepository
from backend.repositories.tasks import TaskRepository


class TaskCompletionService:
    """Validate completion feedback and atomically close a task with an audit event."""

    def __init__(
        self,
        task_repository: TaskRepository,
        completion_repository: TaskCompletionRepository,
    ) -> None:
        self._task_repository = task_repository
        self._completion_repository = completion_repository

    async def complete_task(
        self,
        user_id: UUID,
        task_id: UUID,
        feedback: TaskCompletionFeedback,
    ) -> TaskCompletionResult:
        current_task = await self._task_repository.get_task(user_id, task_id)
        if current_task.status not in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}:
            raise TaskCompletionConflictError("Task cannot be completed from its current state")

        completed_at = datetime.now(UTC)
        metrics = calculate_completion_metrics(current_task, feedback)
        completed_task = replace(
            current_task,
            status=TaskStatus.COMPLETED,
            completed_at=completed_at,
            updated_at=completed_at,
        )
        event = TaskEvent(
            id=uuid4(),
            user_id=user_id,
            task_id=task_id,
            event_type=TaskEventType.COMPLETED,
            metrics=metrics,
            occurred_at=completed_at,
        )
        await self._completion_repository.complete_task(completed_task, event)
        return TaskCompletionResult(task=completed_task, event=event)


def calculate_completion_metrics(
    task: Task,
    feedback: TaskCompletionFeedback,
) -> TaskCompletionMetrics:
    """Calculate signed actual-minus-initial deltas without performing I/O."""
    return TaskCompletionMetrics(
        actual_minutes=feedback.actual_minutes,
        actual_easiness_score=feedback.actual_easiness_score,
        estimated_minutes_snapshot=task.estimated_minutes,
        initial_easiness_score_snapshot=task.initial_easiness_score,
        estimate_delta_minutes=(
            feedback.actual_minutes - task.estimated_minutes
            if task.estimated_minutes is not None
            else None
        ),
        easiness_delta=(
            feedback.actual_easiness_score - task.initial_easiness_score
            if task.initial_easiness_score is not None
            else None
        ),
    )
