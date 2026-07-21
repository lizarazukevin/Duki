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
