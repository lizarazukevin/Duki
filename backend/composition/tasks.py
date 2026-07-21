from typing import cast

import httpx
from fastapi import Request

from backend.config import Settings
from backend.errors import FeatureDisabledError, TaskConfigurationError
from backend.repositories.postgres.supabase_task_events import (
    SupabaseTaskCompletionRepository,
)
from backend.repositories.postgres.supabase_tasks import (
    SupabaseGoalRepository,
    SupabaseTaskRepository,
)
from backend.services.goal_service import GoalService
from backend.services.task_completion_service import TaskCompletionService
from backend.services.task_goal_service import TaskGoalService
from backend.services.task_service import TaskService


def _task_dependencies(request: Request) -> tuple[str, str, httpx.AsyncClient]:
    settings = cast(Settings, request.app.state.settings)
    if not settings.tasks_enabled:
        raise FeatureDisabledError("Task management is not enabled")
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise TaskConfigurationError("Task and goal persistence is not configured")
    return (
        settings.supabase_url,
        settings.supabase_secret_key,
        cast(httpx.AsyncClient, request.app.state.http_client),
    )


def provide_task_service(request: Request) -> TaskService:
    """Compose private task workflows through Supabase PostgREST."""
    supabase_url, secret_key, http_client = _task_dependencies(request)
    return TaskService(
        task_repository=SupabaseTaskRepository(
            http_client=http_client,
            supabase_url=supabase_url,
            secret_key=secret_key,
        )
    )


def provide_task_completion_service(request: Request) -> TaskCompletionService:
    """Compose atomic task completion and audit persistence."""
    supabase_url, secret_key, http_client = _task_dependencies(request)
    return TaskCompletionService(
        task_repository=SupabaseTaskRepository(http_client, supabase_url, secret_key),
        completion_repository=SupabaseTaskCompletionRepository(
            http_client,
            supabase_url,
            secret_key,
        ),
    )


def provide_goal_service(request: Request) -> GoalService:
    """Compose private goal workflows through Supabase PostgREST."""
    supabase_url, secret_key, http_client = _task_dependencies(request)
    return GoalService(
        goal_repository=SupabaseGoalRepository(
            http_client=http_client,
            supabase_url=supabase_url,
            secret_key=secret_key,
        )
    )


def provide_task_goal_service(request: Request) -> TaskGoalService:
    """Compose private task-to-goal membership workflows."""
    supabase_url, secret_key, http_client = _task_dependencies(request)
    return TaskGoalService(
        task_repository=SupabaseTaskRepository(
            http_client=http_client,
            supabase_url=supabase_url,
            secret_key=secret_key,
        ),
        goal_repository=SupabaseGoalRepository(
            http_client=http_client,
            supabase_url=supabase_url,
            secret_key=secret_key,
        ),
    )
