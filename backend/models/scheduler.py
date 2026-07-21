from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from backend.models.tasks import TaskCategory


class ScheduleRankingReason(StrEnum):
    LOW_ENERGY = "low_energy"
    BALANCED_ENERGY = "balanced_energy"
    HIGH_ENERGY = "high_energy"


class UnscheduledReason(StrEnum):
    MISSING_ESTIMATE = "missing_estimate"
    NO_FITTING_BLOCK = "no_fitting_block"


@dataclass(frozen=True, slots=True)
class ScheduledTask:
    task_id: UUID
    title: str
    category: TaskCategory
    start_time: datetime
    end_time: datetime
    estimated_minutes: int
    easiness_score: int | None
    ranking_reason: ScheduleRankingReason

    def __post_init__(self) -> None:
        if self.start_time.utcoffset() is None or self.end_time.utcoffset() is None:
            raise ValueError("Scheduled task timestamps must include a timezone")
        if self.end_time <= self.start_time or self.estimated_minutes <= 0:
            raise ValueError("Scheduled task duration must be positive")


@dataclass(frozen=True, slots=True)
class UnscheduledTask:
    task_id: UUID
    title: str
    reason: UnscheduledReason


@dataclass(frozen=True, slots=True)
class SchedulePlan:
    plan_date: date
    computed_mood_score: float
    available_minutes: int
    scheduled_minutes: int
    items: tuple[ScheduledTask, ...]
    unscheduled: tuple[UnscheduledTask, ...]
