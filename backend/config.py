from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from backend.constants import (
    DEFAULT_GROQ_TASK_EXTRACTION_MODEL,
    DEFAULT_GROQ_TRANSCRIPTION_MODEL,
    DEFAULT_OPENAI_TASK_EXTRACTION_MODEL,
    DEFAULT_OPENAI_TRANSCRIPTION_MODEL,
    DEFAULT_TASK_EXTRACTION_PROVIDER,
    DEFAULT_TRANSCRIPTION_PROVIDER,
)


@dataclass(frozen=True, slots=True)
class Settings:
    app_environment: str
    auth_enabled: bool
    calendar_sync_enabled: bool
    tasks_enabled: bool
    duck_sessions_enabled: bool
    moods_enabled: bool
    scheduler_enabled: bool
    supabase_url: str | None
    supabase_publishable_key: str | None
    supabase_secret_key: str | None
    google_oauth_client_id: str | None
    google_oauth_client_secret: str | None
    transcription_provider: str
    groq_api_key: str | None
    groq_transcription_model: str
    task_extraction_provider: str
    groq_task_extraction_model: str
    openai_api_key: str | None
    openai_transcription_model: str
    openai_task_extraction_model: str
    credential_encryption_keys: tuple[str, ...]
    allowed_oauth_redirect_hosts: frozenset[str]

    @property
    def is_local(self) -> bool:
        return self.app_environment == "local"


def _is_enabled(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes"}


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_environment=os.getenv("APP_ENV", "local").lower(),
        auth_enabled=_is_enabled(os.getenv("AUTH_ENABLED", "false")),
        calendar_sync_enabled=_is_enabled(os.getenv("CALENDAR_SYNC_ENABLED", "false")),
        tasks_enabled=_is_enabled(os.getenv("TASKS_ENABLED", "false")),
        duck_sessions_enabled=_is_enabled(os.getenv("DUCK_SESSIONS_ENABLED", "false")),
        moods_enabled=_is_enabled(os.getenv("MOODS_ENABLED", "false")),
        scheduler_enabled=_is_enabled(os.getenv("SCHEDULER_ENABLED", "false")),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY"),
        supabase_secret_key=os.getenv("SUPABASE_SECRET_KEY"),
        google_oauth_client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        transcription_provider=os.getenv("TRANSCRIPTION_PROVIDER", DEFAULT_TRANSCRIPTION_PROVIDER)
        .strip()
        .lower(),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        groq_transcription_model=os.getenv(
            "GROQ_TRANSCRIPTION_MODEL", DEFAULT_GROQ_TRANSCRIPTION_MODEL
        ),
        task_extraction_provider=os.getenv(
            "TASK_EXTRACTION_PROVIDER", DEFAULT_TASK_EXTRACTION_PROVIDER
        )
        .strip()
        .lower(),
        groq_task_extraction_model=os.getenv(
            "GROQ_TASK_EXTRACTION_MODEL", DEFAULT_GROQ_TASK_EXTRACTION_MODEL
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_transcription_model=os.getenv(
            "OPENAI_TRANSCRIPTION_MODEL", DEFAULT_OPENAI_TRANSCRIPTION_MODEL
        ),
        openai_task_extraction_model=os.getenv(
            "OPENAI_TASK_EXTRACTION_MODEL", DEFAULT_OPENAI_TASK_EXTRACTION_MODEL
        ),
        credential_encryption_keys=tuple(
            key.strip()
            for key in os.getenv("CREDENTIAL_ENCRYPTION_KEYS", "").split(",")
            if key.strip()
        ),
        allowed_oauth_redirect_hosts=frozenset(
            host.strip().lower()
            for host in os.getenv("ALLOWED_OAUTH_REDIRECT_HOSTS", "localhost,127.0.0.1").split(",")
            if host.strip()
        ),
    )
