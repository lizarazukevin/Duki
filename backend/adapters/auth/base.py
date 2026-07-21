from typing import Protocol

from backend.models.auth import AuthenticatedUser


class IdentityAuthorizationAdapter(Protocol):
    """Port for starting an authorization flow with an identity provider."""

    def build_authorization_url(
        self,
        redirect_to: str,
        code_challenge: str,
    ) -> str: ...


class SessionValidationAdapter(Protocol):
    """Port for resolving a provider access token into an authenticated user."""

    async def validate_access_token(self, access_token: str) -> AuthenticatedUser: ...
