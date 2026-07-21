from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import httpx

from backend.errors import (
    DuckSessionConfirmationConflictError,
    DuckSessionNotFoundError,
    DuckSessionPersistenceError,
)
from backend.models.duck_sessions import (
    DuckSession,
    DuckSessionStatus,
    SuggestedTaskAction,
    TaskResolutionDecision,
    TaskResolutionSuggestion,
)
from backend.models.tasks import Task
from backend.repositories.duck_sessions import DuckSessionRepository

_NETWORK_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError)


class SupabaseDuckSessionRepository(DuckSessionRepository):
    """Persist duck-session state and atomically commit generated task trees."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        secret_key: str,
    ) -> None:
        rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._http_client = http_client
        self._sessions_url = f"{rest_url}/duck_sessions"
        self._completion_url = f"{rest_url}/rpc/complete_duck_session"
        self._confirmation_url = f"{rest_url}/rpc/confirm_duck_session"
        self._headers = {"apikey": secret_key, "Prefer": "return=minimal"}

    async def create_session(self, session: DuckSession) -> None:
        await self._write("post", self._sessions_url, self._serialize_session(session))

    async def update_session(self, session: DuckSession) -> None:
        await self._write(
            "patch",
            self._sessions_url,
            self._serialize_session(session),
            {"id": f"eq.{session.id}", "user_id": f"eq.{session.user_id}"},
        )

    async def complete_session(
        self,
        session: DuckSession,
        tasks: Sequence[Task],
    ) -> None:
        if session.status is not DuckSessionStatus.COMPLETED:
            raise ValueError("Only a completed duck session can commit generated tasks")
        if session.transcript is None or session.finished_at is None:
            raise ValueError("Completed duck session is missing persistence data")
        await self._write(
            "post",
            self._completion_url,
            {
                "p_session_id": str(session.id),
                "p_user_id": str(session.user_id),
                "p_transcript": session.transcript,
                "p_root_task_id": str(session.root_task_id),
                "p_finished_at": session.finished_at.isoformat(),
                "p_tasks": [self._serialize_generated_task(task) for task in tasks],
                "p_resolution_suggestions": [
                    self._serialize_resolution(suggestion)
                    for suggestion in session.resolution_suggestions
                ],
            },
        )

    async def get_session(self, user_id: UUID, session_id: UUID) -> DuckSession:
        try:
            response = await self._http_client.get(
                self._sessions_url,
                params={
                    "select": "*",
                    "id": f"eq.{session_id}",
                    "user_id": f"eq.{user_id}",
                    "limit": "1",
                },
                headers={"apikey": self._headers["apikey"]},
            )
        except _NETWORK_ERRORS as error:
            raise DuckSessionPersistenceError("Duck session could not be loaded") from error
        if response.status_code >= 400:
            raise DuckSessionPersistenceError("Duck session could not be loaded")
        try:
            payload: object = response.json()
            if not isinstance(payload, list):
                raise TypeError("Invalid duck session collection")
            if not payload:
                raise DuckSessionNotFoundError("Duck session was not found")
            return self._parse_session(payload[0])
        except DuckSessionNotFoundError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise DuckSessionPersistenceError("Stored duck session is invalid") from error

    async def confirm_session(
        self,
        user_id: UUID,
        session_id: UUID,
        decisions: Sequence[TaskResolutionDecision],
        confirmed_at: datetime,
    ) -> None:
        try:
            response = await self._http_client.post(
                self._confirmation_url,
                headers=self._headers,
                json={
                    "p_user_id": str(user_id),
                    "p_session_id": str(session_id),
                    "p_confirmed_at": confirmed_at.isoformat(),
                    "p_decisions": [self._serialize_decision(item) for item in decisions],
                },
            )
        except _NETWORK_ERRORS as error:
            raise DuckSessionPersistenceError("Duck confirmation could not be saved") from error
        if response.status_code == 404:
            raise DuckSessionNotFoundError("Duck session was not found")
        if response.status_code == 409:
            raise DuckSessionConfirmationConflictError(
                "Duck session cannot be confirmed from its current state"
            )
        if response.status_code >= 400:
            raise DuckSessionPersistenceError("Duck confirmation could not be saved")

    async def _write(
        self,
        method: str,
        url: str,
        payload: dict[str, object],
        parameters: dict[str, str] | None = None,
    ) -> None:
        try:
            response = await self._http_client.request(
                method,
                url,
                params=parameters,
                headers=self._headers,
                json=payload,
            )
        except _NETWORK_ERRORS as error:
            raise DuckSessionPersistenceError("Duck session could not be saved") from error
        if response.status_code >= 400:
            raise DuckSessionPersistenceError("Duck session could not be saved")

    @staticmethod
    def _serialize_session(session: DuckSession) -> dict[str, object]:
        return {
            "id": str(session.id),
            "user_id": str(session.user_id),
            "status": session.status.value,
            "transcript": session.transcript,
            "root_task_id": str(session.root_task_id) if session.root_task_id else None,
            "resolution_suggestions": [
                SupabaseDuckSessionRepository._serialize_resolution(suggestion)
                for suggestion in session.resolution_suggestions
            ],
            "confirmed_resolutions": [
                SupabaseDuckSessionRepository._serialize_decision(decision)
                for decision in session.confirmed_resolutions
            ],
            "confirmed_at": session.confirmed_at.isoformat() if session.confirmed_at else None,
            "failure_code": session.failure_code,
            "finished_at": session.finished_at.isoformat() if session.finished_at else None,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    @staticmethod
    def _serialize_generated_task(task: Task) -> dict[str, object]:
        return {
            "id": str(task.id),
            "parent_task_id": str(task.parent_task_id) if task.parent_task_id else None,
            "title": task.title,
            "description": task.description,
            "category": task.category.value,
            "estimated_minutes": task.estimated_minutes,
            "initial_easiness_score": task.initial_easiness_score,
            "easiness_source": task.easiness_source.value if task.easiness_source else None,
            "position": task.position,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

    @staticmethod
    def _serialize_resolution(
        suggestion: TaskResolutionSuggestion,
    ) -> dict[str, object]:
        return {
            "task_id": str(suggestion.task_id),
            "suggested_action": suggestion.suggested_action.value,
            "actual_minutes": suggestion.actual_minutes,
            "actual_easiness_score": suggestion.actual_easiness_score,
        }

    @staticmethod
    def _serialize_decision(decision: TaskResolutionDecision) -> dict[str, object]:
        return {
            "task_id": str(decision.task_id),
            "action": decision.action.value,
            "actual_minutes": decision.actual_minutes,
            "actual_easiness_score": decision.actual_easiness_score,
        }

    @staticmethod
    def _parse_session(row: object) -> DuckSession:
        if not isinstance(row, dict):
            raise TypeError("Invalid duck session row")
        return DuckSession(
            id=UUID(_required_string(row, "id")),
            user_id=UUID(_required_string(row, "user_id")),
            status=DuckSessionStatus(_required_string(row, "status")),
            transcript=_optional_string(row, "transcript"),
            root_task_id=_optional_uuid(row, "root_task_id"),
            resolution_suggestions=_parse_resolutions(row.get("resolution_suggestions")),
            confirmed_resolutions=_parse_decisions(row.get("confirmed_resolutions")),
            confirmed_at=_optional_datetime(row, "confirmed_at"),
            failure_code=_optional_string(row, "failure_code"),
            finished_at=_optional_datetime(row, "finished_at"),
            created_at=datetime.fromisoformat(_required_string(row, "created_at")),
            updated_at=datetime.fromisoformat(_required_string(row, "updated_at")),
        )


def _required_string(row: dict[str, object], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise TypeError("Invalid stored duck session text")
    return value


def _optional_string(row: dict[str, object], field: str) -> str | None:
    value = row.get(field)
    if value is not None and not isinstance(value, str):
        raise TypeError("Invalid optional duck session text")
    return value


def _optional_uuid(row: dict[str, object], field: str) -> UUID | None:
    value = _optional_string(row, field)
    return UUID(value) if value else None


def _optional_datetime(row: dict[str, object], field: str) -> datetime | None:
    value = _optional_string(row, field)
    return datetime.fromisoformat(value) if value else None


def _parse_resolutions(value: object) -> tuple[TaskResolutionSuggestion, ...]:
    if not isinstance(value, list):
        raise TypeError("Invalid duck session resolutions")
    suggestions: list[TaskResolutionSuggestion] = []
    for item in value:
        if not isinstance(item, dict):
            raise TypeError("Invalid duck session resolution")
        suggestions.append(
            TaskResolutionSuggestion(
                task_id=UUID(_required_string(item, "task_id")),
                suggested_action=SuggestedTaskAction(_required_string(item, "suggested_action")),
                actual_minutes=_optional_int(item, "actual_minutes"),
                actual_easiness_score=_optional_int(item, "actual_easiness_score"),
            )
        )
    return tuple(suggestions)


def _optional_int(row: dict[str, object], field: str) -> int | None:
    value = row.get(field)
    if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
        raise TypeError("Invalid optional duck session number")
    return value


def _parse_decisions(value: object) -> tuple[TaskResolutionDecision, ...]:
    if not isinstance(value, list):
        raise TypeError("Invalid confirmed duck resolutions")
    decisions: list[TaskResolutionDecision] = []
    for item in value:
        if not isinstance(item, dict):
            raise TypeError("Invalid confirmed duck resolution")
        decisions.append(
            TaskResolutionDecision(
                task_id=UUID(_required_string(item, "task_id")),
                action=SuggestedTaskAction(_required_string(item, "action")),
                actual_minutes=_optional_int(item, "actual_minutes"),
                actual_easiness_score=_optional_int(item, "actual_easiness_score"),
            )
        )
    return tuple(decisions)
