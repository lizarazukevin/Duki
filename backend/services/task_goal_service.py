import asyncio
from uuid import UUID

from backend.repositories.tasks import GoalRepository, TaskRepository


class TaskGoalService:
    """Manage user-owned task-to-goal membership."""

    def __init__(
        self,
        task_repository: TaskRepository,
        goal_repository: GoalRepository,
    ) -> None:
        self._task_repository = task_repository
        self._goal_repository = goal_repository

    async def attach_goal(self, user_id: UUID, task_id: UUID, goal_id: UUID) -> None:
        await self._validate_members(user_id, task_id, goal_id)
        await self._task_repository.add_goal(user_id, task_id, goal_id)

    async def detach_goal(self, user_id: UUID, task_id: UUID, goal_id: UUID) -> None:
        await self._validate_members(user_id, task_id, goal_id)
        await self._task_repository.remove_goal(user_id, task_id, goal_id)

    async def _validate_members(
        self,
        user_id: UUID,
        task_id: UUID,
        goal_id: UUID,
    ) -> None:
        await asyncio.gather(
            self._task_repository.get_task(user_id, task_id),
            self._goal_repository.get_goal(user_id, goal_id),
        )
