from typing import Protocol

from backend.models.task_events import TaskEvent
from backend.models.tasks import Task


class TaskCompletionRepository(Protocol):
    """Persistence port for atomically completing a task and writing its audit event."""

    async def complete_task(self, task: Task, event: TaskEvent) -> None: ...
