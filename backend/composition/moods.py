from typing import cast

import httpx
from fastapi import Request

from backend.config import Settings
from backend.errors import FeatureDisabledError, MoodConfigurationError
from backend.repositories.postgres.supabase_calendar import SupabaseCalendarRepository
from backend.repositories.postgres.supabase_moods import SupabaseMoodRepository
from backend.services.mood_computation_service import MoodComputationService
from backend.services.mood_service import MoodService


def provide_mood_service(request: Request) -> MoodService:
    """Compose private mood workflows through cached calendar and mood persistence."""
    settings = cast(Settings, request.app.state.settings)
    if not settings.moods_enabled:
        raise FeatureDisabledError("Mood tracking is not enabled")
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise MoodConfigurationError("Mood persistence is not configured")

    http_client = cast(httpx.AsyncClient, request.app.state.http_client)
    return MoodService(
        mood_repository=SupabaseMoodRepository(
            http_client=http_client,
            supabase_url=settings.supabase_url,
            secret_key=settings.supabase_secret_key,
        ),
        calendar_repository=SupabaseCalendarRepository(
            http_client=http_client,
            supabase_url=settings.supabase_url,
            secret_key=settings.supabase_secret_key,
        ),
        computation_service=MoodComputationService(),
    )
