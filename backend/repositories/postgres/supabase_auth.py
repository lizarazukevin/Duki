from datetime import UTC, datetime
from typing import Any

import httpx

from backend.adapters.security.base import CredentialCipher
from backend.errors import PersistenceError
from backend.models.auth import AuthenticatedUser, GoogleCredentials
from backend.repositories.auth import AuthRepository


class SupabaseAuthRepository(AuthRepository):
    """Persist auth data through Supabase PostgREST using a server-only key."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        secret_key: str,
        credential_cipher: CredentialCipher,
    ) -> None:
        self._http_client = http_client
        self._rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._headers = {
            "apikey": secret_key,
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
        self._credential_cipher = credential_cipher

    async def upsert_user(self, user: AuthenticatedUser) -> None:
        await self._upsert(
            table="users",
            conflict="id",
            payload={
                "id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def save_google_credentials(
        self,
        credentials: GoogleCredentials,
    ) -> None:
        await self._upsert(
            table="google_credentials",
            conflict="user_id",
            payload={
                "user_id": str(credentials.user_id),
                "encrypted_access_token": self._credential_cipher.encrypt(credentials.access_token),
                "encrypted_refresh_token": self._credential_cipher.encrypt(
                    credentials.refresh_token
                ),
                "access_token_expires_at": (
                    credentials.access_token_expires_at.isoformat()
                    if credentials.access_token_expires_at
                    else None
                ),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def _upsert(
        self,
        table: str,
        conflict: str,
        payload: dict[str, Any],
    ) -> None:
        try:
            response = await self._http_client.post(
                f"{self._rest_url}/{table}",
                params={"on_conflict": conflict},
                headers=self._headers,
                json=payload,
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as error:
            raise PersistenceError("Auth data could not be saved") from error
        if response.status_code >= 400:
            raise PersistenceError("Auth data could not be saved")
