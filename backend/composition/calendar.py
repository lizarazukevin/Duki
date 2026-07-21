from typing import cast

import httpx
from fastapi import Request

from backend.adapters.calendar.google import GoogleCalendarAdapter
from backend.adapters.security.fernet import FernetCredentialCipher
from backend.config import Settings
from backend.errors import CalendarConfigurationError, FeatureDisabledError
from backend.repositories.postgres.supabase_auth import SupabaseAuthRepository
from backend.repositories.postgres.supabase_calendar import SupabaseCalendarRepository
from backend.services.calendar_availability_service import CalendarAvailabilityService
from backend.services.calendar_query_service import CalendarQueryService
from backend.services.calendar_sync_service import CalendarSyncService


def provide_calendar_sync_service(request: Request) -> CalendarSyncService:
    """Compose the Google-to-Postgres calendar synchronization workflow."""
    settings = cast(Settings, request.app.state.settings)
    if not settings.calendar_sync_enabled:
        raise FeatureDisabledError("Calendar synchronization is not enabled")
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise CalendarConfigurationError("Calendar persistence is not configured")
    if not settings.credential_encryption_keys:
        raise CalendarConfigurationError("Credential encryption is not configured")
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise CalendarConfigurationError("Google OAuth refresh is not configured")

    http_client = cast(httpx.AsyncClient, request.app.state.http_client)
    credential_cipher = FernetCredentialCipher(settings.credential_encryption_keys)
    return CalendarSyncService(
        calendar_adapter=GoogleCalendarAdapter(
            http_client=http_client,
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
        ),
        auth_repository=SupabaseAuthRepository(
            http_client=http_client,
            supabase_url=settings.supabase_url,
            secret_key=settings.supabase_secret_key,
            credential_cipher=credential_cipher,
        ),
        calendar_repository=SupabaseCalendarRepository(
            http_client=http_client,
            supabase_url=settings.supabase_url,
            secret_key=settings.supabase_secret_key,
        ),
    )


def provide_calendar_query_service(request: Request) -> CalendarQueryService:
    """Compose private cached-calendar reads through PostgREST."""
    settings = cast(Settings, request.app.state.settings)
    if not settings.calendar_sync_enabled:
        raise FeatureDisabledError("Calendar synchronization is not enabled")
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise CalendarConfigurationError("Calendar persistence is not configured")
    http_client = cast(httpx.AsyncClient, request.app.state.http_client)
    return CalendarQueryService(
        calendar_repository=SupabaseCalendarRepository(
            http_client=http_client,
            supabase_url=settings.supabase_url,
            secret_key=settings.supabase_secret_key,
        )
    )


def provide_calendar_availability_service(request: Request) -> CalendarAvailabilityService:
    """Compose private free-block derivation from cached calendar events."""
    settings = cast(Settings, request.app.state.settings)
    if not settings.calendar_sync_enabled:
        raise FeatureDisabledError("Calendar synchronization is not enabled")
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise CalendarConfigurationError("Calendar persistence is not configured")
    http_client = cast(httpx.AsyncClient, request.app.state.http_client)
    return CalendarAvailabilityService(
        calendar_repository=SupabaseCalendarRepository(
            http_client=http_client,
            supabase_url=settings.supabase_url,
            secret_key=settings.supabase_secret_key,
        )
    )
