from typing import Protocol
from uuid import UUID

from backend.models.auth import AuthenticatedUser, GoogleCredentials


class AuthRepository(Protocol):
    """Persistence port for identity profiles and provider credentials."""

    async def upsert_user(self, user: AuthenticatedUser) -> None: ...

    async def save_google_credentials(
        self,
        credentials: GoogleCredentials,
    ) -> None: ...

    async def get_google_credentials(self, user_id: UUID) -> GoogleCredentials: ...
