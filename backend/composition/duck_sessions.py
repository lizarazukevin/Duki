from typing import cast

import httpx
from fastapi import Request

from backend.adapters.task_extraction.base import TaskExtractionAdapter
from backend.adapters.task_extraction.groq import GroqTaskExtractionAdapter
from backend.adapters.task_extraction.openai import OpenAITaskExtractionAdapter
from backend.adapters.voice.base import VoiceAdapter
from backend.adapters.voice.groq import GroqVoiceAdapter
from backend.adapters.voice.openai import OpenAIVoiceAdapter
from backend.config import Settings
from backend.errors import DuckSessionConfigurationError, FeatureDisabledError
from backend.repositories.postgres.supabase_duck_sessions import (
    SupabaseDuckSessionRepository,
)
from backend.repositories.postgres.supabase_tasks import SupabaseTaskRepository
from backend.services.duck_session_confirmation_service import (
    DuckSessionConfirmationService,
)
from backend.services.duck_session_query_service import DuckSessionQueryService
from backend.services.duck_session_service import DuckSessionService
from backend.services.task_deduplication_service import TaskDeduplicationService
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


def _voice_adapter(settings: Settings, http_client: httpx.AsyncClient) -> VoiceAdapter:
    if settings.transcription_provider == "groq":
        if not settings.groq_api_key:
            raise DuckSessionConfigurationError("Groq transcription is not configured")
        return GroqVoiceAdapter(
            http_client=http_client,
            api_key=settings.groq_api_key,
            model=settings.groq_transcription_model,
        )
    if settings.transcription_provider == "openai":
        if not settings.openai_api_key:
            raise DuckSessionConfigurationError("OpenAI transcription is not configured")
        return OpenAIVoiceAdapter(
            http_client=http_client,
            api_key=settings.openai_api_key,
            model=settings.openai_transcription_model,
        )
    raise DuckSessionConfigurationError("Transcription provider is not supported")


def _task_extraction_adapter(
    settings: Settings,
    http_client: httpx.AsyncClient,
) -> TaskExtractionAdapter:
    if settings.task_extraction_provider == "groq":
        if not settings.groq_api_key:
            raise DuckSessionConfigurationError("Groq task extraction is not configured")
        return GroqTaskExtractionAdapter(
            http_client=http_client,
            api_key=settings.groq_api_key,
            model=settings.groq_task_extraction_model,
        )
    if settings.task_extraction_provider == "openai":
        if not settings.openai_api_key:
            raise DuckSessionConfigurationError("OpenAI task extraction is not configured")
        return OpenAITaskExtractionAdapter(
            http_client=http_client,
            api_key=settings.openai_api_key,
            model=settings.openai_task_extraction_model,
        )
    raise DuckSessionConfigurationError("Task extraction provider is not supported")


def provide_duck_session_service(request: Request) -> DuckSessionService:
    """Compose the private voice-to-task workflow from swappable ports."""
    settings, supabase_url, secret_key, http_client = _session_dependencies(request)

    return DuckSessionService(
        voice_adapter=_voice_adapter(settings, http_client),
        task_extraction_adapter=_task_extraction_adapter(settings, http_client),
        session_repository=_session_repository(supabase_url, secret_key, http_client),
        transcript_normalization_service=TranscriptNormalizationService(),
        task_repository=SupabaseTaskRepository(http_client, supabase_url, secret_key),
        task_deduplication_service=TaskDeduplicationService(),
    )


def provide_duck_session_query_service(request: Request) -> DuckSessionQueryService:
    """Compose duck-session reads without requiring processing-provider configuration."""
    _, supabase_url, secret_key, http_client = _session_dependencies(request)
    return DuckSessionQueryService(_session_repository(supabase_url, secret_key, http_client))


def provide_duck_session_confirmation_service(
    request: Request,
) -> DuckSessionConfirmationService:
    """Compose atomic user confirmation without loading voice providers."""
    _, supabase_url, secret_key, http_client = _session_dependencies(request)
    return DuckSessionConfirmationService(
        _session_repository(supabase_url, secret_key, http_client)
    )
