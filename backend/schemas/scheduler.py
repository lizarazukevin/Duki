from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from backend.models.calendar import CalendarSyncWindow
from backend.models.scheduler import SchedulePlan, ScheduleRankingReason, UnscheduledReason
from backend.models.tasks import TaskCategory


class SchedulePlanRequest(BaseModel):
    plan_date: date
    start_time: datetime
    end_time: datetime
    minimum_block_minutes: int = Field(default=15, ge=1, le=480)

    @model_validator(mode="after")
    def validate_plan_window(self) -> Self:
        CalendarSyncWindow(self.start_time, self.end_time)
        if self.start_time.date() != self.plan_date:
            raise ValueError("Plan date must match the window's local start date")
        return self

    def to_window(self) -> CalendarSyncWindow:
        return CalendarSyncWindow(self.start_time, self.end_time)


class ScheduledTaskResponse(BaseModel):
    task_id: UUID
    title: str
    category: TaskCategory
    start_time: datetime
    end_time: datetime
    estimated_minutes: int
    easiness_score: int | None
    ranking_reason: ScheduleRankingReason


class UnscheduledTaskResponse(BaseModel):
    task_id: UUID
    title: str
    reason: UnscheduledReason


class SchedulePlanResponse(BaseModel):
    plan_date: date
    computed_mood_score: float
    available_minutes: int
    scheduled_minutes: int
    items: list[ScheduledTaskResponse]
    unscheduled: list[UnscheduledTaskResponse]

    @classmethod
    def from_domain(cls, plan: SchedulePlan) -> Self:
        return cls(
            plan_date=plan.plan_date,
            computed_mood_score=plan.computed_mood_score,
            available_minutes=plan.available_minutes,
            scheduled_minutes=plan.scheduled_minutes,
            items=[
                ScheduledTaskResponse.model_validate(item, from_attributes=True)
                for item in plan.items
            ],
            unscheduled=[
                UnscheduledTaskResponse.model_validate(item, from_attributes=True)
                for item in plan.unscheduled
            ],
        )
