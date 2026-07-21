from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class TaskEventType(StrEnum):
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class TaskCompletionFeedback:
    actual_minutes: int
    actual_easiness_score: int

    def __post_init__(self) -> None:
        if self.actual_minutes <= 0:
            raise ValueError("Actual task duration must be positive")
        if not 1 <= self.actual_easiness_score <= 5:
            raise ValueError("Actual task easiness score must be between 1 and 5")


@dataclass(frozen=True, slots=True)
class TaskCompletionMetrics:
    actual_minutes: int
    actual_easiness_score: int
    estimated_minutes_snapshot: int | None
    initial_easiness_score_snapshot: int | None
    estimate_delta_minutes: int | None
    easiness_delta: int | None

    def __post_init__(self) -> None:
        TaskCompletionFeedback(self.actual_minutes, self.actual_easiness_score)
        expected_estimate_delta = (
            self.actual_minutes - self.estimated_minutes_snapshot
            if self.estimated_minutes_snapshot is not None
            else None
        )
        expected_easiness_delta = (
            self.actual_easiness_score - self.initial_easiness_score_snapshot
            if self.initial_easiness_score_snapshot is not None
            else None
        )
        if self.estimated_minutes_snapshot is not None and self.estimated_minutes_snapshot <= 0:
            raise ValueError("Task estimate snapshot must be positive")
        if (
            self.initial_easiness_score_snapshot is not None
            and not 1 <= self.initial_easiness_score_snapshot <= 5
        ):
            raise ValueError("Task easiness snapshot must be between 1 and 5")
        if self.estimate_delta_minutes != expected_estimate_delta:
            raise ValueError("Task estimate delta is inconsistent")
        if self.easiness_delta != expected_easiness_delta:
            raise ValueError("Task easiness delta is inconsistent")


@dataclass(frozen=True, slots=True)
class TaskEvent:
    id: UUID
    user_id: UUID
    task_id: UUID
    event_type: TaskEventType
    metrics: TaskCompletionMetrics
    occurred_at: datetime

    def __post_init__(self) -> None:
        if self.occurred_at.utcoffset() is None:
            raise ValueError("Task event timestamp must include a timezone")
