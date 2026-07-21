from typing import cast

import httpx
from fastapi import Request

from backend.config import Settings
from backend.errors import FeatureDisabledError, SchedulerConfigurationError
from backend.repositories.postgres.supabase_calendar import SupabaseCalendarRepository
from backend.repositories.postgres.supabase_moods import SupabaseMoodRepository
from backend.repositories.postgres.supabase_tasks import SupabaseTaskRepository
from backend.services.calendar_availability_service import CalendarAvailabilityService
from backend.services.scheduler_service import SchedulerService


def provide_scheduler_service(request: Request) -> SchedulerService:
    """Compose private scheduling from tasks, mood, and primary-calendar gaps."""
    settings = cast(Settings, request.app.state.settings)
    if not settings.scheduler_enabled:
        raise FeatureDisabledError("Scheduling is not enabled")
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise SchedulerConfigurationError("Scheduler persistence is not configured")

    http_client = cast(httpx.AsyncClient, request.app.state.http_client)
    calendar_repository = SupabaseCalendarRepository(
        http_client=http_client,
        supabase_url=settings.supabase_url,
        secret_key=settings.supabase_secret_key,
    )
    return SchedulerService(
        task_repository=SupabaseTaskRepository(
            http_client=http_client,
            supabase_url=settings.supabase_url,
            secret_key=settings.supabase_secret_key,
        ),
        mood_repository=SupabaseMoodRepository(
            http_client=http_client,
            supabase_url=settings.supabase_url,
            secret_key=settings.supabase_secret_key,
        ),
        availability_service=CalendarAvailabilityService(calendar_repository),
    )
