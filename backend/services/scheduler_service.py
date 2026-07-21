import asyncio
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from uuid import UUID

from backend.models.calendar import CalendarFreeBlock, CalendarSyncWindow
from backend.models.scheduler import (
    ScheduledTask,
    SchedulePlan,
    ScheduleRankingReason,
    UnscheduledReason,
    UnscheduledTask,
)
from backend.models.tasks import Task, TaskStatus
from backend.repositories.moods import MoodRepository
from backend.repositories.tasks import TaskRepository
from backend.services.calendar_availability_service import CalendarAvailabilityService

LOW_ENERGY_MAX = 2.5
HIGH_ENERGY_MIN = 3.5
DEFAULT_EASINESS_SCORE = 3


class SchedulerService:
    """Combine tasks, primary-calendar gaps, and today's mood into a daily plan."""

    def __init__(
        self,
        task_repository: TaskRepository,
        mood_repository: MoodRepository,
        availability_service: CalendarAvailabilityService,
    ) -> None:
        self._task_repository = task_repository
        self._mood_repository = mood_repository
        self._availability_service = availability_service

    async def build_plan(
        self,
        user_id: UUID,
        plan_date: date,
        window: CalendarSyncWindow,
        minimum_block_minutes: int,
    ) -> SchedulePlan:
        tasks, mood, free_blocks = await asyncio.gather(
            self._task_repository.list_tasks(user_id, include_archived=False),
            self._mood_repository.get_mood(user_id, plan_date),
            self._availability_service.list_free_blocks(
                user_id,
                window,
                minimum_block_minutes,
            ),
        )
        return build_schedule_plan(
            tasks,
            free_blocks,
            mood.computed_mood_score,
            plan_date,
        )


def build_schedule_plan(
    tasks: Sequence[Task],
    free_blocks: Sequence[CalendarFreeBlock],
    computed_mood_score: float,
    plan_date: date,
) -> SchedulePlan:
    """Build a deterministic best-fit plan without hidden I/O or persistence."""
    if not 1 <= computed_mood_score <= 5:
        raise ValueError("Computed mood score must be between 1 and 5")

    parent_ids = {task.parent_task_id for task in tasks if task.parent_task_id is not None}
    candidates = [
        task
        for task in tasks
        if task.id not in parent_ids
        and task.status in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}
        and (task.scheduled_date is None or task.scheduled_date <= plan_date)
    ]
    ranking_reason = _ranking_reason(computed_mood_score)
    ranked_tasks = sorted(
        (task for task in candidates if task.estimated_minutes is not None),
        key=lambda task: _task_rank(task, computed_mood_score, plan_date),
    )
    unscheduled = [
        UnscheduledTask(task.id, task.title, UnscheduledReason.MISSING_ESTIMATE)
        for task in candidates
        if task.estimated_minutes is None
    ]
    remaining_blocks = [[block.start_time, block.end_time] for block in free_blocks]
    scheduled: list[ScheduledTask] = []

    for task in ranked_tasks:
        estimated_minutes = task.estimated_minutes
        if estimated_minutes is None:
            continue
        block_index = _best_fit_block(remaining_blocks, estimated_minutes)
        if block_index is None:
            unscheduled.append(
                UnscheduledTask(task.id, task.title, UnscheduledReason.NO_FITTING_BLOCK)
            )
            continue
        start_time, block_end = remaining_blocks[block_index]
        end_time = start_time + timedelta(minutes=estimated_minutes)
        scheduled.append(
            ScheduledTask(
                task_id=task.id,
                title=task.title,
                category=task.category,
                start_time=start_time,
                end_time=end_time,
                estimated_minutes=estimated_minutes,
                easiness_score=task.initial_easiness_score,
                ranking_reason=ranking_reason,
            )
        )
        if end_time == block_end:
            remaining_blocks.pop(block_index)
        else:
            remaining_blocks[block_index][0] = end_time

    scheduled.sort(key=lambda item: (item.start_time, item.task_id))
    unscheduled.sort(key=lambda item: (item.reason, item.task_id))
    return SchedulePlan(
        plan_date=plan_date,
        computed_mood_score=computed_mood_score,
        available_minutes=sum(block.duration_minutes for block in free_blocks),
        scheduled_minutes=sum(item.estimated_minutes for item in scheduled),
        items=tuple(scheduled),
        unscheduled=tuple(unscheduled),
    )


def _task_rank(task: Task, mood_score: float, plan_date: date) -> tuple[object, ...]:
    easiness = task.initial_easiness_score or DEFAULT_EASINESS_SCORE
    is_overdue = task.due_at is not None and task.due_at.date() <= plan_date
    due_timestamp = task.due_at.timestamp() if task.due_at is not None else float("inf")
    estimated_minutes = task.estimated_minutes or 0
    if mood_score <= LOW_ENERGY_MAX:
        energy_rank = (-easiness, estimated_minutes)
    elif mood_score >= HIGH_ENERGY_MIN:
        energy_rank = (easiness, -estimated_minutes)
    else:
        energy_rank = (abs(easiness - DEFAULT_EASINESS_SCORE), estimated_minutes)
    return (
        not is_overdue,
        *energy_rank,
        due_timestamp,
        task.position,
        task.created_at,
        task.id,
    )


def _ranking_reason(mood_score: float) -> ScheduleRankingReason:
    if mood_score <= LOW_ENERGY_MAX:
        return ScheduleRankingReason.LOW_ENERGY
    if mood_score >= HIGH_ENERGY_MIN:
        return ScheduleRankingReason.HIGH_ENERGY
    return ScheduleRankingReason.BALANCED_ENERGY


def _best_fit_block(
    blocks: Sequence[list[datetime]],
    estimated_minutes: int,
) -> int | None:
    required_duration = timedelta(minutes=estimated_minutes)
    fitting = [
        (block_end - block_start - required_duration, block_start, index)
        for index, (block_start, block_end) in enumerate(blocks)
        if block_end - block_start >= required_duration
    ]
    return min(fitting)[2] if fitting else None
