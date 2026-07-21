from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.models.tasks import (
    EasinessSource,
    TaskCategory,
    TaskDetail,
    TaskDraft,
    TaskStatus,
)


class TaskCreateRequest(BaseModel):
    parent_task_id: UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    category: TaskCategory = TaskCategory.WORK
    estimated_minutes: int | None = Field(default=None, gt=0)
    initial_easiness_score: int | None = Field(default=None, ge=1, le=5)
    easiness_source: EasinessSource | None = None
    scheduled_date: date | None = None
    due_at: datetime | None = None
    position: int = Field(default=0, ge=0)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, title: str) -> str:
        stripped_title = title.strip()
        if not stripped_title:
            raise ValueError("Task title cannot be blank")
        return stripped_title

    @model_validator(mode="after")
    def validate_domain_rules(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> TaskDraft:
        return TaskDraft(
            parent_task_id=self.parent_task_id,
            title=self.title,
            description=self.description,
            category=self.category,
            estimated_minutes=self.estimated_minutes,
            initial_easiness_score=self.initial_easiness_score,
            easiness_source=self.easiness_source,
            scheduled_date=self.scheduled_date,
            due_at=self.due_at,
            position=self.position,
        )


class TaskResponse(BaseModel):
    id: UUID
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
    goal_ids: list[UUID]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, detail: TaskDetail) -> Self:
        task = detail.task
        return cls(
            id=task.id,
            parent_task_id=task.parent_task_id,
            title=task.title,
            description=task.description,
            category=task.category,
            status=task.status,
            estimated_minutes=task.estimated_minutes,
            initial_easiness_score=task.initial_easiness_score,
            easiness_source=task.easiness_source,
            scheduled_date=task.scheduled_date,
            due_at=task.due_at,
            position=task.position,
            completed_at=task.completed_at,
            goal_ids=list(detail.goal_ids),
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
