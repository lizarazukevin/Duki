from typing import cast

from fastapi import Request

from backend.adapters.auth.supabase import SupabaseGoogleIdentityAdapter
from backend.config import Settings
from backend.errors import AuthConfigurationError, FeatureDisabledError
from backend.services.identity_auth_service import IdentityAuthService


def provide_identity_auth_service(request: Request) -> IdentityAuthService:
    """Build the auth workflow at the HTTP boundary with injected adapters."""
    settings = cast(Settings, request.app.state.settings)
    if not settings.auth_enabled:
        raise FeatureDisabledError("Authentication is not enabled")
    if not settings.supabase_url:
        raise AuthConfigurationError("Supabase URL is not configured")
    return IdentityAuthService(
        identity_adapter=SupabaseGoogleIdentityAdapter(settings.supabase_url),
        allowed_redirect_hosts=settings.allowed_oauth_redirect_hosts,
    )
