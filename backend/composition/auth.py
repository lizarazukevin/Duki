from typing import Annotated, cast

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.adapters.auth.supabase import (
    SupabaseAuthorizationCodeExchangeAdapter,
    SupabaseGoogleAuthorizationAdapter,
    SupabaseSessionValidationAdapter,
)
from backend.adapters.security.fernet import FernetCredentialCipher
from backend.config import Settings
from backend.errors import (
    AuthConfigurationError,
    AuthenticationError,
    FeatureDisabledError,
)
from backend.models.auth import AuthenticatedUser
from backend.repositories.postgres.supabase_auth import SupabaseAuthRepository
from backend.services.identity_authorization_service import (
    IdentityAuthorizationService,
)
from backend.services.session_exchange_service import SessionExchangeService
from backend.services.session_validation_service import SessionValidationService

bearer_scheme = HTTPBearer(auto_error=False)


def _auth_settings(request: Request) -> Settings:
    settings = cast(Settings, request.app.state.settings)
    if not settings.auth_enabled:
        raise FeatureDisabledError("Authentication is not enabled")
    if not settings.supabase_url:
        raise AuthConfigurationError("Supabase URL is not configured")
    return settings


def provide_identity_authorization_service(
    request: Request,
) -> IdentityAuthorizationService:
    """Compose authorization URL generation at the HTTP boundary."""
    settings = _auth_settings(request)
    return IdentityAuthorizationService(
        authorization_adapter=SupabaseGoogleAuthorizationAdapter(settings.supabase_url or ""),
        allowed_redirect_hosts=settings.allowed_oauth_redirect_hosts,
    )


def provide_session_validation_service(request: Request) -> SessionValidationService:
    """Compose live session validation using the application's pooled client."""
    settings = _auth_settings(request)
    if not settings.supabase_publishable_key:
        raise AuthConfigurationError("Supabase publishable key is not configured")
    http_client = cast(httpx.AsyncClient, request.app.state.http_client)
    return SessionValidationService(
        session_adapter=SupabaseSessionValidationAdapter(
            http_client=http_client,
            supabase_url=settings.supabase_url or "",
            publishable_key=settings.supabase_publishable_key,
        )
    )


def provide_session_exchange_service(request: Request) -> SessionExchangeService:
    """Compose PKCE exchange with encrypted provider-credential persistence."""
    settings = _auth_settings(request)
    if not settings.supabase_publishable_key:
        raise AuthConfigurationError("Supabase publishable key is not configured")
    if not settings.supabase_secret_key:
        raise AuthConfigurationError("Supabase secret key is not configured")
    if not settings.credential_encryption_keys:
        raise AuthConfigurationError("Credential encryption is not configured")
    http_client = cast(httpx.AsyncClient, request.app.state.http_client)
    return SessionExchangeService(
        exchange_adapter=SupabaseAuthorizationCodeExchangeAdapter(
            http_client=http_client,
            supabase_url=settings.supabase_url or "",
            publishable_key=settings.supabase_publishable_key,
        ),
        auth_repository=SupabaseAuthRepository(
            http_client=http_client,
            supabase_url=settings.supabase_url or "",
            secret_key=settings.supabase_secret_key,
            credential_cipher=FernetCredentialCipher(settings.credential_encryption_keys),
        ),
    )


async def require_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    service: Annotated[
        SessionValidationService,
        Depends(provide_session_validation_service),
    ],
) -> AuthenticatedUser:
    """Resolve the bearer token into the current authenticated user."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("A bearer access token is required")
    return await service.current_user(credentials.credentials)
