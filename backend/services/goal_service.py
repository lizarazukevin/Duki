from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.models.tasks import Goal, GoalDraft, GoalStatus, GoalUpdate
from backend.repositories.tasks import GoalRepository


class GoalService:
    """Manage user-owned goals through a provider-neutral repository."""

    def __init__(self, goal_repository: GoalRepository) -> None:
        self._goal_repository = goal_repository

    async def create_goal(self, user_id: UUID, draft: GoalDraft) -> Goal:
        now = datetime.now(UTC)
        goal = Goal(
            id=uuid4(),
            user_id=user_id,
            title=draft.title.strip(),
            description=draft.description,
            status=GoalStatus.ACTIVE,
            target_date=draft.target_date,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        await self._goal_repository.create_goal(goal)
        return goal

    async def get_goal(self, user_id: UUID, goal_id: UUID) -> Goal:
        return await self._goal_repository.get_goal(user_id, goal_id)

    async def list_goals(self, user_id: UUID, include_archived: bool) -> tuple[Goal, ...]:
        return await self._goal_repository.list_goals(user_id, include_archived)

    async def update_goal(self, user_id: UUID, goal_id: UUID, update: GoalUpdate) -> Goal:
        current_goal = await self._goal_repository.get_goal(user_id, goal_id)
        now = datetime.now(UTC)
        completed_at = None
        if update.status is GoalStatus.COMPLETED:
            completed_at = current_goal.completed_at or now
        goal = replace(
            current_goal,
            title=update.title.strip(),
            description=update.description,
            status=update.status,
            target_date=update.target_date,
            completed_at=completed_at,
            updated_at=now,
        )
        await self._goal_repository.update_goal(goal)
        return goal

    async def delete_goal(self, user_id: UUID, goal_id: UUID) -> None:
        await self._goal_repository.delete_goal(user_id, goal_id)
