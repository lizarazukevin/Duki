from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

from backend.adapters.security.base import CredentialCipher
from backend.errors import GoogleCredentialsNotFoundError, PersistenceError
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

    async def get_google_credentials(self, user_id: UUID) -> GoogleCredentials:
        try:
            response = await self._http_client.get(
                f"{self._rest_url}/google_credentials",
                params={
                    "select": (
                        "encrypted_access_token,encrypted_refresh_token,access_token_expires_at"
                    ),
                    "user_id": f"eq.{user_id}",
                    "limit": "1",
                },
                headers={"apikey": self._headers["apikey"]},
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as error:
            raise PersistenceError("Google credentials could not be loaded") from error
        if response.status_code >= 400:
            raise PersistenceError("Google credentials could not be loaded")
        try:
            payload: object = response.json()
            if not isinstance(payload, list) or not payload:
                raise GoogleCredentialsNotFoundError("Google Calendar is not connected")
            row = payload[0]
            if not isinstance(row, dict):
                raise TypeError("Invalid credential row")
            encrypted_access_token = row["encrypted_access_token"]
            encrypted_refresh_token = row["encrypted_refresh_token"]
            expires_at = row.get("access_token_expires_at")
            if not isinstance(encrypted_access_token, str) or not isinstance(
                encrypted_refresh_token, str
            ):
                raise TypeError("Invalid encrypted credential")
            if expires_at is not None and not isinstance(expires_at, str):
                raise TypeError("Invalid credential expiry")
            return GoogleCredentials(
                user_id=user_id,
                access_token=self._credential_cipher.decrypt(encrypted_access_token),
                refresh_token=self._credential_cipher.decrypt(encrypted_refresh_token),
                access_token_expires_at=(
                    datetime.fromisoformat(expires_at) if expires_at is not None else None
                ),
            )
        except GoogleCredentialsNotFoundError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise PersistenceError("Stored Google credentials are invalid") from error

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
