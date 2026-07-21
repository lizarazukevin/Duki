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
    access_token_expires_at: datetime
