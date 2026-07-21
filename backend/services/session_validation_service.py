from backend.adapters.auth.base import SessionValidationAdapter
from backend.models.auth import AuthenticatedUser


class SessionValidationService:
    """Validate identity sessions without depending on a concrete provider."""

    def __init__(self, session_adapter: SessionValidationAdapter) -> None:
        self._session_adapter = session_adapter

    async def current_user(self, access_token: str) -> AuthenticatedUser:
        return await self._session_adapter.validate_access_token(access_token)
