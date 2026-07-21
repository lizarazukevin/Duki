from datetime import date, datetime
from uuid import UUID

import httpx

from backend.errors import (
    GoalNotFoundError,
    GoalPersistenceError,
    TaskNotFoundError,
    TaskPersistenceError,
)
from backend.models.tasks import (
    EasinessSource,
    Goal,
    GoalStatus,
    Task,
    TaskCategory,
    TaskGoalLink,
    TaskStatus,
)
from backend.repositories.tasks import GoalRepository, TaskRepository

_NETWORK_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError)


class SupabaseTaskRepository(TaskRepository):
    """Persist tasks and goal membership through Supabase PostgREST."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        secret_key: str,
    ) -> None:
        rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._http_client = http_client
        self._tasks_url = f"{rest_url}/tasks"
        self._task_goals_url = f"{rest_url}/task_goals"
        self._headers = {"apikey": secret_key, "Prefer": "return=minimal"}

    async def create_task(self, task: Task) -> None:
        await self._write("post", self._tasks_url, self._serialize_task(task))

    async def update_task(self, task: Task) -> None:
        parameters = {"id": f"eq.{task.id}", "user_id": f"eq.{task.user_id}"}
        await self._write(
            "patch",
            self._tasks_url,
            self._serialize_task(task),
            parameters,
        )

    async def get_task(self, user_id: UUID, task_id: UUID) -> Task:
        parameters = {
            "select": "*",
            "id": f"eq.{task_id}",
            "user_id": f"eq.{user_id}",
            "limit": "1",
        }
        try:
            response = await self._http_client.get(
                self._tasks_url,
                params=parameters,
                headers={"apikey": self._headers["apikey"]},
            )
        except _NETWORK_ERRORS as error:
            raise TaskPersistenceError("Task could not be loaded") from error
        if response.status_code >= 400:
            raise TaskPersistenceError("Task could not be loaded")
        try:
            payload: object = response.json()
            if not isinstance(payload, list):
                raise TypeError("Invalid task collection")
            if not payload:
                raise TaskNotFoundError("Task was not found")
            return _parse_task(payload[0])
        except TaskNotFoundError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise TaskPersistenceError("Stored task is invalid") from error

    async def delete_task(self, user_id: UUID, task_id: UUID) -> None:
        await self.get_task(user_id, task_id)
        await self._write(
            "delete",
            self._tasks_url,
            None,
            {"id": f"eq.{task_id}", "user_id": f"eq.{user_id}"},
        )

    async def list_tasks(self, user_id: UUID, include_archived: bool) -> tuple[Task, ...]:
        parameters = {
            "select": "*",
            "user_id": f"eq.{user_id}",
            "order": "position.asc,created_at.asc,id.asc",
        }
        if not include_archived:
            parameters["status"] = "neq.archived"
        rows = await self._read_all(
            self._tasks_url,
            parameters,
            "Tasks could not be loaded",
        )
        try:
            return tuple(_parse_task(row) for row in rows)
        except (KeyError, TypeError, ValueError) as error:
            raise TaskPersistenceError("Stored tasks are invalid") from error

    async def list_goal_links(self, user_id: UUID) -> tuple[TaskGoalLink, ...]:
        rows = await self._read_all(
            self._task_goals_url,
            {
                "select": "task_id,goal_id",
                "user_id": f"eq.{user_id}",
                "order": "created_at.asc,task_id.asc,goal_id.asc",
            },
            "Task goals could not be loaded",
        )
        try:
            return tuple(
                TaskGoalLink(
                    task_id=UUID(_required_string(row, "task_id")),
                    goal_id=UUID(_required_string(row, "goal_id")),
                )
                for row in rows
            )
        except (KeyError, TypeError, ValueError) as error:
            raise TaskPersistenceError("Stored task goals are invalid") from error

    async def add_goal(self, user_id: UUID, task_id: UUID, goal_id: UUID) -> None:
        await self._write(
            "post",
            self._task_goals_url,
            {"user_id": str(user_id), "task_id": str(task_id), "goal_id": str(goal_id)},
            {"on_conflict": "task_id,goal_id"},
            prefer="resolution=merge-duplicates,return=minimal",
        )

    async def remove_goal(self, user_id: UUID, task_id: UUID, goal_id: UUID) -> None:
        await self._write(
            "delete",
            self._task_goals_url,
            None,
            {
                "user_id": f"eq.{user_id}",
                "task_id": f"eq.{task_id}",
                "goal_id": f"eq.{goal_id}",
            },
        )

    async def list_goal_ids(self, user_id: UUID, task_id: UUID) -> tuple[UUID, ...]:
        try:
            response = await self._http_client.get(
                self._task_goals_url,
                params={
                    "select": "goal_id",
                    "user_id": f"eq.{user_id}",
                    "task_id": f"eq.{task_id}",
                    "order": "created_at.asc",
                },
                headers={"apikey": self._headers["apikey"]},
            )
        except _NETWORK_ERRORS as error:
            raise TaskPersistenceError("Task goals could not be loaded") from error
        if response.status_code >= 400:
            raise TaskPersistenceError("Task goals could not be loaded")
        try:
            payload: object = response.json()
            if not isinstance(payload, list):
                raise TypeError("Invalid task goal collection")
            return tuple(UUID(_required_string(row, "goal_id")) for row in payload)
        except (KeyError, TypeError, ValueError) as error:
            raise TaskPersistenceError("Stored task goals are invalid") from error

    async def _write(
        self,
        method: str,
        url: str,
        payload: dict[str, object] | None,
        parameters: dict[str, str] | None = None,
        *,
        prefer: str | None = None,
    ) -> None:
        headers = self._headers if prefer is None else {**self._headers, "Prefer": prefer}
        try:
            response = await self._http_client.request(
                method,
                url,
                params=parameters,
                headers=headers,
                json=payload,
            )
        except _NETWORK_ERRORS as error:
            raise TaskPersistenceError("Task data could not be saved") from error
        if response.status_code >= 400:
            raise TaskPersistenceError("Task data could not be saved")

    async def _read_all(
        self,
        url: str,
        parameters: dict[str, str],
        error_message: str,
    ) -> tuple[object, ...]:
        page_size = 500
        offset = 0
        rows: list[object] = []
        while True:
            try:
                response = await self._http_client.get(
                    url,
                    params={**parameters, "limit": str(page_size), "offset": str(offset)},
                    headers={"apikey": self._headers["apikey"]},
                )
            except _NETWORK_ERRORS as error:
                raise TaskPersistenceError(error_message) from error
            if response.status_code >= 400:
                raise TaskPersistenceError(error_message)
            try:
                payload: object = response.json()
                if not isinstance(payload, list):
                    raise TypeError("Invalid task collection")
            except (TypeError, ValueError) as error:
                raise TaskPersistenceError(error_message) from error
            rows.extend(payload)
            if len(payload) < page_size:
                return tuple(rows)
            offset += page_size

    @staticmethod
    def _serialize_task(task: Task) -> dict[str, object]:
        return {
            "id": str(task.id),
            "user_id": str(task.user_id),
            "parent_task_id": str(task.parent_task_id) if task.parent_task_id else None,
            "title": task.title,
            "description": task.description,
            "category": task.category.value,
            "status": task.status.value,
            "estimated_minutes": task.estimated_minutes,
            "initial_easiness_score": task.initial_easiness_score,
            "easiness_source": task.easiness_source.value if task.easiness_source else None,
            "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
            "due_at": task.due_at.isoformat() if task.due_at else None,
            "position": task.position,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }


class SupabaseGoalRepository(GoalRepository):
    """Persist goals through Supabase PostgREST."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        secret_key: str,
    ) -> None:
        self._http_client = http_client
        self._goals_url = f"{supabase_url.rstrip('/')}/rest/v1/goals"
        self._headers = {"apikey": secret_key, "Prefer": "return=minimal"}

    async def create_goal(self, goal: Goal) -> None:
        await self._write("post", self._serialize_goal(goal))

    async def update_goal(self, goal: Goal) -> None:
        await self._write(
            "patch",
            self._serialize_goal(goal),
            {"id": f"eq.{goal.id}", "user_id": f"eq.{goal.user_id}"},
        )

    async def get_goal(self, user_id: UUID, goal_id: UUID) -> Goal:
        try:
            response = await self._http_client.get(
                self._goals_url,
                params={
                    "select": "*",
                    "id": f"eq.{goal_id}",
                    "user_id": f"eq.{user_id}",
                    "limit": "1",
                },
                headers={"apikey": self._headers["apikey"]},
            )
        except _NETWORK_ERRORS as error:
            raise GoalPersistenceError("Goal could not be loaded") from error
        if response.status_code >= 400:
            raise GoalPersistenceError("Goal could not be loaded")
        try:
            payload: object = response.json()
            if not isinstance(payload, list):
                raise TypeError("Invalid goal collection")
            if not payload:
                raise GoalNotFoundError("Goal was not found")
            return _parse_goal(payload[0])
        except GoalNotFoundError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise GoalPersistenceError("Stored goal is invalid") from error

    async def delete_goal(self, user_id: UUID, goal_id: UUID) -> None:
        await self.get_goal(user_id, goal_id)
        await self._write(
            "delete",
            None,
            {"id": f"eq.{goal_id}", "user_id": f"eq.{user_id}"},
        )

    async def _write(
        self,
        method: str,
        payload: dict[str, object] | None,
        parameters: dict[str, str] | None = None,
    ) -> None:
        try:
            response = await self._http_client.request(
                method,
                self._goals_url,
                params=parameters,
                headers=self._headers,
                json=payload,
            )
        except _NETWORK_ERRORS as error:
            raise GoalPersistenceError("Goal data could not be saved") from error
        if response.status_code >= 400:
            raise GoalPersistenceError("Goal data could not be saved")

    @staticmethod
    def _serialize_goal(goal: Goal) -> dict[str, object]:
        return {
            "id": str(goal.id),
            "user_id": str(goal.user_id),
            "title": goal.title,
            "description": goal.description,
            "status": goal.status.value,
            "target_date": goal.target_date.isoformat() if goal.target_date else None,
            "completed_at": goal.completed_at.isoformat() if goal.completed_at else None,
            "created_at": goal.created_at.isoformat(),
            "updated_at": goal.updated_at.isoformat(),
        }


def _parse_task(row: object) -> Task:
    if not isinstance(row, dict):
        raise TypeError("Invalid task row")
    return Task(
        id=UUID(_required_string(row, "id")),
        user_id=UUID(_required_string(row, "user_id")),
        parent_task_id=_optional_uuid(row, "parent_task_id"),
        title=_required_string(row, "title"),
        description=_optional_string(row, "description"),
        category=TaskCategory(_required_string(row, "category")),
        status=TaskStatus(_required_string(row, "status")),
        estimated_minutes=_optional_int(row, "estimated_minutes"),
        initial_easiness_score=_optional_int(row, "initial_easiness_score"),
        easiness_source=_optional_enum(row, "easiness_source", EasinessSource),
        scheduled_date=_optional_date(row, "scheduled_date"),
        due_at=_optional_datetime(row, "due_at"),
        position=_required_int(row, "position"),
        completed_at=_optional_datetime(row, "completed_at"),
        created_at=datetime.fromisoformat(_required_string(row, "created_at")),
        updated_at=datetime.fromisoformat(_required_string(row, "updated_at")),
    )


def _parse_goal(row: object) -> Goal:
    if not isinstance(row, dict):
        raise TypeError("Invalid goal row")
    return Goal(
        id=UUID(_required_string(row, "id")),
        user_id=UUID(_required_string(row, "user_id")),
        title=_required_string(row, "title"),
        description=_optional_string(row, "description"),
        status=GoalStatus(_required_string(row, "status")),
        target_date=_optional_date(row, "target_date"),
        completed_at=_optional_datetime(row, "completed_at"),
        created_at=datetime.fromisoformat(_required_string(row, "created_at")),
        updated_at=datetime.fromisoformat(_required_string(row, "updated_at")),
    )


def _required_string(row: object, field: str) -> str:
    if not isinstance(row, dict):
        raise TypeError("Invalid stored row")
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise TypeError("Invalid stored text")
    return value


def _optional_string(row: dict[str, object], field: str) -> str | None:
    value = row.get(field)
    if value is not None and not isinstance(value, str):
        raise TypeError("Invalid optional stored text")
    return value


def _required_int(row: dict[str, object], field: str) -> int:
    value = row.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("Invalid stored integer")
    return value


def _optional_int(row: dict[str, object], field: str) -> int | None:
    value = row.get(field)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("Invalid optional stored integer")
    return value


def _optional_uuid(row: dict[str, object], field: str) -> UUID | None:
    value = _optional_string(row, field)
    return UUID(value) if value else None


def _optional_date(row: dict[str, object], field: str) -> date | None:
    value = _optional_string(row, field)
    return date.fromisoformat(value) if value else None


def _optional_datetime(row: dict[str, object], field: str) -> datetime | None:
    value = _optional_string(row, field)
    return datetime.fromisoformat(value) if value else None


def _optional_enum(
    row: dict[str, object],
    field: str,
    enum_type: type[EasinessSource],
) -> EasinessSource | None:
    value = _optional_string(row, field)
    return enum_type(value) if value else None
