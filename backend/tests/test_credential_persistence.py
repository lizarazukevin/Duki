import json
import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from cryptography.fernet import Fernet

from backend.adapters.security.fernet import FernetCredentialCipher
from backend.errors import CredentialEncryptionError
from backend.models.auth import GoogleCredentials
from backend.repositories.postgres.supabase_auth import SupabaseAuthRepository


class CredentialEncryptionTests(unittest.TestCase):
    def test_round_trip_and_key_rotation(self) -> None:
        primary_key = Fernet.generate_key().decode("ascii")
        previous_key = Fernet.generate_key().decode("ascii")
        old_cipher = FernetCredentialCipher((previous_key,))
        rotated_cipher = FernetCredentialCipher((primary_key, previous_key))

        old_token = old_cipher.encrypt("provider-refresh-token")
        new_token = rotated_cipher.encrypt("provider-refresh-token")

        self.assertEqual(rotated_cipher.decrypt(old_token), "provider-refresh-token")
        self.assertEqual(rotated_cipher.decrypt(new_token), "provider-refresh-token")
        self.assertNotIn("provider-refresh-token", new_token)

    def test_tampered_ciphertext_is_rejected(self) -> None:
        key = Fernet.generate_key().decode("ascii")
        cipher = FernetCredentialCipher((key,))
        encrypted = cipher.encrypt("provider-refresh-token")
        tampered = f"{encrypted[:-1]}{'A' if encrypted[-1] != 'A' else 'B'}"

        with self.assertRaises(CredentialEncryptionError):
            cipher.decrypt(tampered)


class SupabaseAuthRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_tokens_are_encrypted_before_persistence(self) -> None:
        key = Fernet.generate_key().decode("ascii")
        cipher = FernetCredentialCipher((key,))
        captured_payload: dict[str, object] = {}

        def capture(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["apikey"], "secret-key")
            self.assertNotIn("authorization", request.headers)
            captured_payload.update(json.loads(request.content))
            return httpx.Response(201)

        async with httpx.AsyncClient(transport=httpx.MockTransport(capture)) as client:
            repository = SupabaseAuthRepository(
                http_client=client,
                supabase_url="https://project.supabase.co",
                secret_key="secret-key",
                credential_cipher=cipher,
            )
            await repository.save_google_credentials(
                GoogleCredentials(
                    user_id=uuid4(),
                    access_token="provider-access-token",
                    refresh_token="provider-refresh-token",
                    access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
                )
            )

        serialized_payload = json.dumps(captured_payload)
        self.assertNotIn("provider-access-token", serialized_payload)
        self.assertNotIn("provider-refresh-token", serialized_payload)
        self.assertEqual(
            cipher.decrypt(str(captured_payload["encrypted_refresh_token"])),
            "provider-refresh-token",
        )
