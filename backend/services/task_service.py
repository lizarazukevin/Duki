import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.errors import InvalidTaskHierarchyError
from backend.models.tasks import (
    Task,
    TaskDetail,
    TaskDraft,
    TaskGoalLink,
    TaskStatus,
    TaskTreeNode,
    TaskUpdate,
)
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

    async def update_task(
        self,
        user_id: UUID,
        task_id: UUID,
        update: TaskUpdate,
    ) -> TaskDetail:
        current_task = await self._task_repository.get_task(user_id, task_id)
        await self._validate_parent(user_id, task_id, update.parent_task_id)
        task = replace(
            current_task,
            parent_task_id=update.parent_task_id,
            title=update.title.strip(),
            description=update.description,
            category=update.category,
            status=update.status,
            estimated_minutes=update.estimated_minutes,
            initial_easiness_score=update.initial_easiness_score,
            easiness_source=update.easiness_source,
            scheduled_date=update.scheduled_date,
            due_at=update.due_at,
            position=update.position,
            updated_at=datetime.now(UTC),
        )
        await self._task_repository.update_task(task)
        goal_ids = await self._task_repository.list_goal_ids(user_id, task_id)
        return TaskDetail(task=task, goal_ids=goal_ids)

    async def delete_task(self, user_id: UUID, task_id: UUID) -> None:
        await self._task_repository.delete_task(user_id, task_id)

    async def list_task_tree(
        self,
        user_id: UUID,
        include_archived: bool,
    ) -> tuple[TaskTreeNode, ...]:
        tasks, goal_links = await asyncio.gather(
            self._task_repository.list_tasks(user_id, include_archived),
            self._task_repository.list_goal_links(user_id),
        )
        return build_task_tree(tasks, goal_links)

    async def _validate_parent(
        self,
        user_id: UUID,
        task_id: UUID,
        parent_task_id: UUID | None,
    ) -> None:
        ancestor_id = parent_task_id
        visited_ids: set[UUID] = set()
        while ancestor_id is not None:
            if ancestor_id == task_id or ancestor_id in visited_ids:
                raise InvalidTaskHierarchyError("Task hierarchy cannot contain a cycle")
            visited_ids.add(ancestor_id)
            ancestor = await self._task_repository.get_task(user_id, ancestor_id)
            ancestor_id = ancestor.parent_task_id


def build_task_tree(
    tasks: tuple[Task, ...],
    goal_links: tuple[TaskGoalLink, ...],
) -> tuple[TaskTreeNode, ...]:
    """Build a deterministic hierarchy without performing I/O."""
    tasks_by_id = {task.id: task for task in tasks}
    goal_ids_by_task: dict[UUID, list[UUID]] = {}
    for link in goal_links:
        if link.task_id in tasks_by_id:
            goal_ids_by_task.setdefault(link.task_id, []).append(link.goal_id)

    children_by_parent: dict[UUID | None, list[Task]] = {}
    for task in tasks:
        parent_id = task.parent_task_id if task.parent_task_id in tasks_by_id else None
        children_by_parent.setdefault(parent_id, []).append(task)
    for children in children_by_parent.values():
        children.sort(key=lambda task: (task.position, task.created_at, task.id))

    visited_ids: set[UUID] = set()

    def build_node(task: Task, ancestor_ids: frozenset[UUID]) -> TaskTreeNode:
        if task.id in ancestor_ids:
            raise InvalidTaskHierarchyError("Stored task hierarchy contains a cycle")
        visited_ids.add(task.id)
        path = ancestor_ids | {task.id}
        return TaskTreeNode(
            task=TaskDetail(
                task=task,
                goal_ids=tuple(goal_ids_by_task.get(task.id, ())),
            ),
            children=tuple(
                build_node(child, path) for child in children_by_parent.get(task.id, ())
            ),
        )

    roots = tuple(build_node(task, frozenset()) for task in children_by_parent.get(None, ()))
    if len(visited_ids) != len(tasks_by_id):
        raise InvalidTaskHierarchyError("Stored task hierarchy contains a cycle")
    return roots
