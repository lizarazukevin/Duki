import httpx

from backend.errors import (
    TaskCompletionConflictError,
    TaskNotFoundError,
    TaskPersistenceError,
)
from backend.models.task_events import TaskEvent
from backend.models.tasks import Task
from backend.repositories.task_events import TaskCompletionRepository

_NETWORK_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError)


class SupabaseTaskCompletionRepository(TaskCompletionRepository):
    """Complete a task and append its audit event through one Postgres transaction."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        secret_key: str,
    ) -> None:
        self._http_client = http_client
        self._completion_url = f"{supabase_url.rstrip('/')}/rest/v1/rpc/complete_task"
        self._headers = {"apikey": secret_key, "Prefer": "return=minimal"}

    async def complete_task(self, task: Task, event: TaskEvent) -> None:
        if event.user_id != task.user_id or event.task_id != task.id:
            raise ValueError("Completion event ownership must match its task")
        try:
            response = await self._http_client.post(
                self._completion_url,
                headers=self._headers,
                json={
                    "p_user_id": str(task.user_id),
                    "p_task_id": str(task.id),
                    "p_event_id": str(event.id),
                    "p_actual_minutes": event.metrics.actual_minutes,
                    "p_actual_easiness_score": event.metrics.actual_easiness_score,
                    "p_estimated_minutes_snapshot": (event.metrics.estimated_minutes_snapshot),
                    "p_initial_easiness_score_snapshot": (
                        event.metrics.initial_easiness_score_snapshot
                    ),
                    "p_completed_at": event.occurred_at.isoformat(),
                },
            )
        except _NETWORK_ERRORS as error:
            raise TaskPersistenceError("Task completion could not be saved") from error
        if response.status_code == 404:
            raise TaskNotFoundError("Task was not found")
        if response.status_code == 409:
            raise TaskCompletionConflictError("Task cannot be completed from its current state")
        if response.status_code >= 400:
            raise TaskPersistenceError("Task completion could not be saved")
