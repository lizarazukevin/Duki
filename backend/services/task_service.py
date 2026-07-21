from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.models.tasks import Task, TaskDetail, TaskDraft, TaskStatus
from backend.repositories.tasks import TaskRepository


class TaskService:
    """Create and retrieve user-owned tasks through a persistence port."""

    def __init__(self, task_repository: TaskRepository) -> None:
        self._task_repository = task_repository

    async def create_task(self, user_id: UUID, draft: TaskDraft) -> TaskDetail:
        if draft.parent_task_id is not None:
            await self._task_repository.get_task(user_id, draft.parent_task_id)

        now = datetime.now(UTC)
        task = Task(
            id=uuid4(),
            user_id=user_id,
            parent_task_id=draft.parent_task_id,
            title=draft.title.strip(),
            description=draft.description,
            category=draft.category,
            status=TaskStatus.PENDING,
            estimated_minutes=draft.estimated_minutes,
            initial_easiness_score=draft.initial_easiness_score,
            easiness_source=draft.easiness_source,
            scheduled_date=draft.scheduled_date,
            due_at=draft.due_at,
            position=draft.position,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        await self._task_repository.create_task(task)
        return TaskDetail(task=task, goal_ids=())

    async def get_task(self, user_id: UUID, task_id: UUID) -> TaskDetail:
        task = await self._task_repository.get_task(user_id, task_id)
        goal_ids = await self._task_repository.list_goal_ids(user_id, task_id)
        return TaskDetail(task=task, goal_ids=goal_ids)
