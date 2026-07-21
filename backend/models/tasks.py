from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class TaskCategory(StrEnum):
    WORK = "work"
    CHORE = "chore"
    PERSONAL = "personal"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class EasinessSource(StrEnum):
    USER = "user"
    INFERRED = "inferred"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class Task:
    """A user-owned task independent of its persistence representation."""

    id: UUID
    user_id: UUID
    parent_task_id: UUID | None
    title: str
    description: str | None
    category: TaskCategory
    status: TaskStatus
    estimated_minutes: int | None
    initial_easiness_score: int | None
    easiness_source: EasinessSource | None
    scheduled_date: date | None
    due_at: datetime | None
    position: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TaskDraft:
    """Validated fields accepted when a user creates a task."""

    parent_task_id: UUID | None
    title: str
    description: str | None
    category: TaskCategory
    estimated_minutes: int | None
    initial_easiness_score: int | None
    easiness_source: EasinessSource | None
    scheduled_date: date | None
    due_at: datetime | None
    position: int

    def __post_init__(self) -> None:
        _validate_editable_fields(
            title=self.title,
            description=self.description,
            estimated_minutes=self.estimated_minutes,
            initial_easiness_score=self.initial_easiness_score,
            easiness_source=self.easiness_source,
            due_at=self.due_at,
            position=self.position,
        )


@dataclass(frozen=True, slots=True)
class TaskUpdate:
    """Validated editable task state supplied by a full replacement request."""

    parent_task_id: UUID | None
    title: str
    description: str | None
    category: TaskCategory
    status: TaskStatus
    estimated_minutes: int | None
    initial_easiness_score: int | None
    easiness_source: EasinessSource | None
    scheduled_date: date | None
    due_at: datetime | None
    position: int

    def __post_init__(self) -> None:
        _validate_editable_fields(
            title=self.title,
            description=self.description,
            estimated_minutes=self.estimated_minutes,
            initial_easiness_score=self.initial_easiness_score,
            easiness_source=self.easiness_source,
            due_at=self.due_at,
            position=self.position,
        )
        if self.status is TaskStatus.COMPLETED:
            raise ValueError("Task completion requires the dedicated completion workflow")


@dataclass(frozen=True, slots=True)
class TaskDetail:
    task: Task
    goal_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class TaskGoalLink:
    task_id: UUID
    goal_id: UUID


@dataclass(frozen=True, slots=True)
class TaskTreeNode:
    task: TaskDetail
    children: tuple[TaskTreeNode, ...]


@dataclass(frozen=True, slots=True)
class Goal:
    """A user-owned goal that may group multiple tasks."""

    id: UUID
    user_id: UUID
    title: str
    description: str | None
    status: GoalStatus
    target_date: date | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _validate_editable_fields(
    *,
    title: str,
    description: str | None,
    estimated_minutes: int | None,
    initial_easiness_score: int | None,
    easiness_source: EasinessSource | None,
    due_at: datetime | None,
    position: int,
) -> None:
    if not title.strip() or len(title) > 500:
        raise ValueError("Task title must contain between 1 and 500 characters")
    if description is not None and len(description) > 10000:
        raise ValueError("Task description cannot exceed 10000 characters")
    if estimated_minutes is not None and estimated_minutes <= 0:
        raise ValueError("Task estimate must be positive")
    if initial_easiness_score is not None and not 1 <= initial_easiness_score <= 5:
        raise ValueError("Task easiness score must be between 1 and 5")
    if (initial_easiness_score is None) != (easiness_source is None):
        raise ValueError("Task easiness score and source must be provided together")
    if due_at is not None and due_at.utcoffset() is None:
        raise ValueError("Task due time must include a timezone")
    if position < 0:
        raise ValueError("Task position cannot be negative")
