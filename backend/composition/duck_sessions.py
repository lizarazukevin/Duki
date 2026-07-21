from typing import cast

import httpx
from fastapi import Request

from backend.adapters.task_extraction.openai import OpenAITaskExtractionAdapter
from backend.adapters.voice.openai import OpenAIVoiceAdapter
from backend.config import Settings
from backend.errors import DuckSessionConfigurationError, FeatureDisabledError
from backend.repositories.postgres.supabase_duck_sessions import (
    SupabaseDuckSessionRepository,
)
from backend.services.duck_session_query_service import DuckSessionQueryService
from backend.services.duck_session_service import DuckSessionService
from backend.services.transcript_normalization_service import TranscriptNormalizationService


def _session_dependencies(
    request: Request,
) -> tuple[Settings, str, str, httpx.AsyncClient]:
    settings = cast(Settings, request.app.state.settings)
    if not settings.duck_sessions_enabled:
        raise FeatureDisabledError("Duck sessions are not enabled")
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise DuckSessionConfigurationError("Duck session persistence is not configured")
    return (
        settings,
        settings.supabase_url,
        settings.supabase_secret_key,
        cast(httpx.AsyncClient, request.app.state.http_client),
    )


def _session_repository(
    supabase_url: str,
    secret_key: str,
    http_client: httpx.AsyncClient,
) -> SupabaseDuckSessionRepository:
    return SupabaseDuckSessionRepository(
        http_client=http_client,
        supabase_url=supabase_url,
        secret_key=secret_key,
    )


def provide_duck_session_service(request: Request) -> DuckSessionService:
    """Compose the private voice-to-task workflow from swappable ports."""
    settings, supabase_url, secret_key, http_client = _session_dependencies(request)
    if not settings.openai_api_key:
        raise DuckSessionConfigurationError("Voice processing is not configured")

    return DuckSessionService(
        voice_adapter=OpenAIVoiceAdapter(
            http_client=http_client,
            api_key=settings.openai_api_key,
            model=settings.openai_transcription_model,
        ),
        task_extraction_adapter=OpenAITaskExtractionAdapter(
            http_client=http_client,
            api_key=settings.openai_api_key,
            model=settings.openai_task_extraction_model,
        ),
        session_repository=_session_repository(supabase_url, secret_key, http_client),
        transcript_normalization_service=TranscriptNormalizationService(),
    )


def provide_duck_session_query_service(request: Request) -> DuckSessionQueryService:
    """Compose duck-session reads without requiring processing-provider configuration."""
    _, supabase_url, secret_key, http_client = _session_dependencies(request)
    return DuckSessionQueryService(_session_repository(supabase_url, secret_key, http_client))
