from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.models.tasks import Goal, GoalDraft, GoalStatus, GoalUpdate


class GoalCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    target_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, title: str) -> str:
        stripped_title = title.strip()
        if not stripped_title:
            raise ValueError("Goal title cannot be blank")
        return stripped_title

    def to_domain(self) -> GoalDraft:
        return GoalDraft(
            title=self.title,
            description=self.description,
            target_date=self.target_date,
        )


class GoalUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(max_length=10000)
    status: GoalStatus
    target_date: date | None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, title: str) -> str:
        stripped_title = title.strip()
        if not stripped_title:
            raise ValueError("Goal title cannot be blank")
        return stripped_title

    @model_validator(mode="after")
    def validate_domain_rules(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> GoalUpdate:
        return GoalUpdate(
            title=self.title,
            description=self.description,
            status=self.status,
            target_date=self.target_date,
        )


class GoalResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    status: GoalStatus
    target_date: date | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, goal: Goal) -> Self:
        return cls(
            id=goal.id,
            title=goal.title,
            description=goal.description,
            status=goal.status,
            target_date=goal.target_date,
            completed_at=goal.completed_at,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )


class GoalListResponse(BaseModel):
    items: list[GoalResponse]
