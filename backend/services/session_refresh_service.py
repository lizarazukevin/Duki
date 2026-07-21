from backend.adapters.auth.base import SessionRefreshAdapter
from backend.models.auth import SessionTokens


class SessionRefreshService:
    """Rotate an existing refresh token into a replacement identity session."""

    def __init__(self, refresh_adapter: SessionRefreshAdapter) -> None:
        self._refresh_adapter = refresh_adapter

    async def refresh(self, refresh_token: str) -> SessionTokens:
        return await self._refresh_adapter.refresh_session(refresh_token)
