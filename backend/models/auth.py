from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: UUID
    email: str
    display_name: str | None
    avatar_url: str | None


@dataclass(frozen=True, slots=True)
class GoogleCredentials:
    user_id: UUID
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class ExchangedSession:
    """Provider-neutral session plus credentials needed by backend integrations."""

    user: AuthenticatedUser
    access_token: str
    refresh_token: str
    expires_at: datetime
    provider_access_token: str
    provider_refresh_token: str


@dataclass(frozen=True, slots=True)
class SessionTokens:
    """A renewable provider-neutral identity session."""

    user: AuthenticatedUser
    access_token: str
    refresh_token: str
    expires_at: datetime
