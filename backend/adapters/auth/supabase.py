import json
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx

from backend.adapters.auth.base import (
    IdentityAuthorizationAdapter,
    SessionValidationAdapter,
)
from backend.errors import AuthenticationError, IdentityProviderUnavailableError
from backend.models.auth import AuthenticatedUser

GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"


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
            "code_challenge": code_challenge,
            "code_challenge_method": "s256",
            "query_params": json.dumps(
                {"access_type": "offline", "prompt": "consent"},
                separators=(",", ":"),
            ),
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
            return self._parse_user(payload)
        except (KeyError, TypeError, ValueError) as error:
            raise IdentityProviderUnavailableError(
                "The identity provider returned an invalid user"
            ) from error

    @staticmethod
    def _parse_user(payload: dict[str, Any]) -> AuthenticatedUser:
        metadata = payload.get("user_metadata") or {}
        if not isinstance(metadata, dict):
            raise TypeError("Invalid user metadata")
        email = payload.get("email")
        if not isinstance(email, str) or not email:
            raise ValueError("Missing user email")
        return AuthenticatedUser(
            id=UUID(payload["id"]),
            email=email,
            display_name=SupabaseSessionValidationAdapter._optional_string(
                metadata.get("full_name") or metadata.get("name")
            ),
            avatar_url=SupabaseSessionValidationAdapter._optional_string(
                metadata.get("avatar_url") or metadata.get("picture")
            ),
        )

    @staticmethod
    def _optional_string(value: object) -> str | None:
        return value if isinstance(value, str) else None
