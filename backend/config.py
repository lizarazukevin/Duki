from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True, slots=True)
class Settings:
    app_environment: str
    auth_enabled: bool
    calendar_sync_enabled: bool
    supabase_url: str | None
    supabase_publishable_key: str | None
    supabase_secret_key: str | None
    google_oauth_client_id: str | None
    google_oauth_client_secret: str | None
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
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY"),
        supabase_secret_key=os.getenv("SUPABASE_SECRET_KEY"),
        google_oauth_client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
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
