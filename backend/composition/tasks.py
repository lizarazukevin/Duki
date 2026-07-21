from typing import cast

import httpx
from fastapi import Request

from backend.config import Settings
from backend.errors import FeatureDisabledError, TaskConfigurationError
from backend.repositories.postgres.supabase_tasks import SupabaseTaskRepository
from backend.services.task_service import TaskService


def provide_task_service(request: Request) -> TaskService:
    """Compose private task workflows through Supabase PostgREST."""
    settings = cast(Settings, request.app.state.settings)
    if not settings.tasks_enabled:
        raise FeatureDisabledError("Task management is not enabled")
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise TaskConfigurationError("Task persistence is not configured")
    http_client = cast(httpx.AsyncClient, request.app.state.http_client)
    return TaskService(
        task_repository=SupabaseTaskRepository(
            http_client=http_client,
            supabase_url=settings.supabase_url,
            secret_key=settings.supabase_secret_key,
        )
    )
