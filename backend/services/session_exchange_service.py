from backend.adapters.auth.base import AuthorizationCodeExchangeAdapter
from backend.models.auth import ExchangedSession, GoogleCredentials
from backend.repositories.auth import AuthRepository


class SessionExchangeService:
    """Complete PKCE sign-in and persist credentials before releasing the session."""

    def __init__(
        self,
        exchange_adapter: AuthorizationCodeExchangeAdapter,
        auth_repository: AuthRepository,
    ) -> None:
        self._exchange_adapter = exchange_adapter
        self._auth_repository = auth_repository

    async def exchange(
        self,
        auth_code: str,
        auth_code_verifier: str,
    ) -> ExchangedSession:
        session = await self._exchange_adapter.exchange_code(
            auth_code=auth_code,
            auth_code_verifier=auth_code_verifier,
        )
        await self._auth_repository.upsert_user(session.user)
        await self._auth_repository.save_google_credentials(
            GoogleCredentials(
                user_id=session.user.id,
                access_token=session.provider_access_token,
                refresh_token=session.provider_refresh_token,
                access_token_expires_at=None,
            )
        )
        return session
