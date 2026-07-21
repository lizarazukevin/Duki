from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx

from backend.adapters.auth.base import (
    AuthorizationCodeExchangeAdapter,
    IdentityAuthorizationAdapter,
    SessionRefreshAdapter,
    SessionValidationAdapter,
)
from backend.errors import (
    AuthenticationError,
    AuthorizationExchangeError,
    IdentityProviderUnavailableError,
    SessionRefreshError,
)
from backend.models.auth import AuthenticatedUser, ExchangedSession, SessionTokens

GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"


def _parse_authenticated_user(payload: dict[str, Any]) -> AuthenticatedUser:
    metadata = payload.get("user_metadata") or {}
    if not isinstance(metadata, dict):
        raise TypeError("Invalid user metadata")
    email = payload.get("email")
    if not isinstance(email, str) or not email:
        raise ValueError("Missing user email")
    return AuthenticatedUser(
        id=UUID(payload["id"]),
        email=email,
        display_name=_optional_string(metadata.get("full_name") or metadata.get("name")),
        avatar_url=_optional_string(metadata.get("avatar_url") or metadata.get("picture")),
    )


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _parse_session_tokens(payload: dict[str, Any]) -> SessionTokens:
    user_payload = payload["user"]
    if not isinstance(user_payload, dict):
        raise TypeError("Invalid user payload")
    access_token = payload["access_token"]
    refresh_token = payload["refresh_token"]
    if not isinstance(access_token, str) or not access_token:
        raise ValueError("Missing access token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise ValueError("Missing refresh token")
    expires_at = payload.get("expires_at")
    if isinstance(expires_at, int | float) and not isinstance(expires_at, bool):
        expiry = datetime.fromtimestamp(expires_at, UTC)
    else:
        expires_in = payload.get("expires_in")
        if not isinstance(expires_in, int) or isinstance(expires_in, bool) or expires_in <= 0:
            raise TypeError("Invalid session expiry")
        expiry = datetime.now(UTC) + timedelta(seconds=expires_in)
    return SessionTokens(
        user=_parse_authenticated_user(user_payload),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expiry,
    )


class SupabaseGoogleAuthorizationAdapter(IdentityAuthorizationAdapter):
    """Translate an authorization request into Supabase's Google OAuth URL."""

    def __init__(self, supabase_url: str) -> None:
        self._supabase_url = supabase_url.rstrip("/")

    def build_authorization_url(
        self,
        redirect_to: str,
        code_challenge: str,
    ) -> str:
        parameters = {
            "provider": "google",
            "redirect_to": redirect_to,
            "scopes": GOOGLE_CALENDAR_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "code_challenge": code_challenge,
            "code_challenge_method": "s256",
        }
        return f"{self._supabase_url}/auth/v1/authorize?{urlencode(parameters)}"


class SupabaseSessionValidationAdapter(SessionValidationAdapter):
    """Translate Supabase Auth responses into provider-neutral user models."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        publishable_key: str,
    ) -> None:
        self._http_client = http_client
        self._user_url = f"{supabase_url.rstrip('/')}/auth/v1/user"
        self._publishable_key = publishable_key

    async def validate_access_token(self, access_token: str) -> AuthenticatedUser:
        try:
            response = await self._http_client.get(
                self._user_url,
                headers={
                    "apikey": self._publishable_key,
                    "Authorization": f"Bearer {access_token}",
                },
            )
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise IdentityProviderUnavailableError(
                "Session validation is temporarily unavailable"
            ) from error
        if response.status_code in {401, 403}:
            raise AuthenticationError("The session is invalid or expired")
        if response.status_code >= 400:
            raise IdentityProviderUnavailableError("Session validation is temporarily unavailable")
        try:
            payload: object = response.json()
            if not isinstance(payload, dict):
                raise TypeError("Invalid user payload")
            return _parse_authenticated_user(payload)
        except (KeyError, TypeError, ValueError) as error:
            raise IdentityProviderUnavailableError(
                "The identity provider returned an invalid user"
            ) from error


class SupabaseAuthorizationCodeExchangeAdapter(AuthorizationCodeExchangeAdapter):
    """Exchange a PKCE authorization code and normalize the Supabase session."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        publishable_key: str,
    ) -> None:
        self._http_client = http_client
        self._token_url = f"{supabase_url.rstrip('/')}/auth/v1/token"
        self._publishable_key = publishable_key

    async def exchange_code(
        self,
        auth_code: str,
        auth_code_verifier: str,
    ) -> ExchangedSession:
        try:
            response = await self._http_client.post(
                self._token_url,
                params={"grant_type": "pkce"},
                headers={"apikey": self._publishable_key},
                json={
                    "auth_code": auth_code,
                    "code_verifier": auth_code_verifier,
                },
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as error:
            raise IdentityProviderUnavailableError(
                "Authorization code exchange is temporarily unavailable"
            ) from error
        if response.status_code in {400, 401, 403}:
            raise AuthorizationExchangeError("The authorization code or verifier is invalid")
        if response.status_code >= 400:
            raise IdentityProviderUnavailableError(
                "Authorization code exchange is temporarily unavailable"
            )
        try:
            payload: object = response.json()
            if not isinstance(payload, dict):
                raise TypeError("Invalid session payload")
            return self._parse_session(payload)
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise IdentityProviderUnavailableError(
                "The identity provider returned an invalid session"
            ) from error

    @staticmethod
    def _parse_session(payload: dict[str, Any]) -> ExchangedSession:
        session = _parse_session_tokens(payload)
        provider_access_token = payload.get("provider_token")
        provider_refresh_token = payload.get("provider_refresh_token")
        if (
            not isinstance(provider_access_token, str)
            or not provider_access_token
            or not isinstance(provider_refresh_token, str)
            or not provider_refresh_token
        ):
            raise AuthorizationExchangeError(
                "Google did not return offline credentials; authorize again"
            )
        return ExchangedSession(
            user=session.user,
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at,
            provider_access_token=provider_access_token,
            provider_refresh_token=provider_refresh_token,
        )


class SupabaseSessionRefreshAdapter(SessionRefreshAdapter):
    """Rotate a Supabase refresh token and normalize the replacement session."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        publishable_key: str,
    ) -> None:
        self._http_client = http_client
        self._token_url = f"{supabase_url.rstrip('/')}/auth/v1/token"
        self._publishable_key = publishable_key

    async def refresh_session(self, refresh_token: str) -> SessionTokens:
        try:
            response = await self._http_client.post(
                self._token_url,
                params={"grant_type": "refresh_token"},
                headers={"apikey": self._publishable_key},
                json={"refresh_token": refresh_token},
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as error:
            raise IdentityProviderUnavailableError(
                "Session refresh is temporarily unavailable"
            ) from error
        if response.status_code in {400, 401, 403}:
            raise SessionRefreshError("The refresh token is invalid or already used")
        if response.status_code >= 400:
            raise IdentityProviderUnavailableError("Session refresh is temporarily unavailable")
        try:
            payload: object = response.json()
            if not isinstance(payload, dict):
                raise TypeError("Invalid session payload")
            return _parse_session_tokens(payload)
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise IdentityProviderUnavailableError(
                "The identity provider returned an invalid session"
            ) from error
