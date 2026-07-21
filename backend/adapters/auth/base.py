from typing import Protocol

from backend.models.auth import AuthenticatedUser, ExchangedSession


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


class AuthorizationCodeExchangeAdapter(Protocol):
    """Port for exchanging a completed OAuth authorization code for a session."""

    async def exchange_code(
        self,
        auth_code: str,
        auth_code_verifier: str,
    ) -> ExchangedSession: ...
