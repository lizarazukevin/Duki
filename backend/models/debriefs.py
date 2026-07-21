from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class DebriefResolutionType(StrEnum):
    CARRY_FORWARD = "carry_forward"
    ARCHIVE = "archive"


@dataclass(frozen=True, slots=True)
class DebriefTaskResolution:
    task_id: UUID
    resolution: DebriefResolutionType
    carry_forward_date: date | None

    def __post_init__(self) -> None:
        if self.resolution is DebriefResolutionType.CARRY_FORWARD:
            if self.carry_forward_date is None:
                raise ValueError("Carry-forward resolution requires a date")
        elif self.carry_forward_date is not None:
            raise ValueError("Archived resolution cannot have a carry-forward date")


@dataclass(frozen=True, slots=True)
class DailyDebriefDraft:
    debrief_date: date
    evening_mood_score: int
    task_resolutions: tuple[DebriefTaskResolution, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.evening_mood_score, int)
            or isinstance(self.evening_mood_score, bool)
            or not 1 <= self.evening_mood_score <= 5
        ):
            raise ValueError("Evening mood score must be between 1 and 5")
        task_ids = [resolution.task_id for resolution in self.task_resolutions]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Each task can be resolved only once per debrief")
        if any(
            resolution.carry_forward_date is not None
            and resolution.carry_forward_date <= self.debrief_date
            for resolution in self.task_resolutions
        ):
            raise ValueError("Carry-forward date must be after the debrief date")


@dataclass(frozen=True, slots=True)
class DailyDebrief:
    id: UUID
    user_id: UUID
    debrief_date: date
    morning_mood_score_snapshot: float
    evening_mood_score: int
    mood_delta: float
    completed_task_count: int
    carried_forward_task_count: int
    archived_task_count: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not 1 <= self.morning_mood_score_snapshot <= 5:
            raise ValueError("Morning mood snapshot must be between 1 and 5")
        if not 1 <= self.evening_mood_score <= 5:
            raise ValueError("Evening mood score must be between 1 and 5")
        expected_delta = round(
            self.evening_mood_score - self.morning_mood_score_snapshot,
            3,
        )
        if round(self.mood_delta, 3) != expected_delta:
            raise ValueError("Debrief mood delta is inconsistent")
        if (
            min(
                self.completed_task_count,
                self.carried_forward_task_count,
                self.archived_task_count,
            )
            < 0
        ):
            raise ValueError("Debrief task counts cannot be negative")
        if self.created_at.utcoffset() is None or self.updated_at.utcoffset() is None:
            raise ValueError("Debrief timestamps must include a timezone")
