import json
import unittest
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx
from pydantic import ValidationError

from backend.adapters.auth.supabase import (
    GOOGLE_CALENDAR_SCOPE,
    SupabaseGoogleAuthorizationAdapter,
    SupabaseSessionValidationAdapter,
)
from backend.errors import (
    AuthenticationError,
    IdentityProviderUnavailableError,
    RedirectNotAllowedError,
)
from backend.schemas.auth import GoogleAuthorizeRequest
from backend.services.identity_authorization_service import (
    IdentityAuthorizationService,
)

PKCE_CHALLENGE = "A" * 43


class GoogleAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = SupabaseGoogleAuthorizationAdapter("https://project.supabase.co/")
        self.service = IdentityAuthorizationService(
            self.adapter,
            frozenset({"localhost"}),
        )

    def test_authorization_url_requests_calendar_and_offline_consent(self) -> None:
        url = self.service.authorization_url(
            "http://localhost:3000/auth/callback",
            PKCE_CHALLENGE,
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/auth/v1/authorize")
        self.assertEqual(query["provider"], ["google"])
        self.assertEqual(query["scopes"], [GOOGLE_CALENDAR_SCOPE])
        self.assertEqual(query["code_challenge"], [PKCE_CHALLENGE])
        self.assertEqual(query["code_challenge_method"], ["s256"])
        self.assertEqual(
            json.loads(query["query_params"][0]),
            {"access_type": "offline", "prompt": "consent"},
        )

    def test_unapproved_redirect_host_is_rejected(self) -> None:
        with self.assertRaises(RedirectNotAllowedError):
            self.service.authorization_url(
                "https://attacker.example/auth/callback",
                PKCE_CHALLENGE,
            )

    def test_invalid_pkce_challenge_is_rejected_at_boundary(self) -> None:
        with self.assertRaises(ValidationError):
            GoogleAuthorizeRequest.model_validate(
                {
                    "redirect_to": "http://localhost:3000/auth/callback",
                    "code_challenge": "too-short",
                }
            )


class SupabaseSessionValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_session_returns_provider_neutral_user(self) -> None:
        user_id = uuid4()

        def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["apikey"], "publishable-key")
            self.assertEqual(request.headers["authorization"], "Bearer session-token")
            return httpx.Response(
                200,
                json={
                    "id": str(user_id),
                    "email": "duck@example.com",
                    "user_metadata": {"full_name": "Ducky"},
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            adapter = SupabaseSessionValidationAdapter(
                client,
                "https://project.supabase.co",
                "publishable-key",
            )
            user = await adapter.validate_access_token("session-token")

        self.assertEqual(user.id, user_id)
        self.assertEqual(user.display_name, "Ducky")

    async def test_expired_session_is_rejected(self) -> None:
        transport = httpx.MockTransport(lambda request: httpx.Response(401))
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = SupabaseSessionValidationAdapter(
                client,
                "https://project.supabase.co",
                "publishable-key",
            )
            with self.assertRaises(AuthenticationError):
                await adapter.validate_access_token("expired-token")

    async def test_malformed_provider_response_is_translated(self) -> None:
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = SupabaseSessionValidationAdapter(
                client,
                "https://project.supabase.co",
                "publishable-key",
            )
            with self.assertRaises(IdentityProviderUnavailableError):
                await adapter.validate_access_token("session-token")

    async def test_provider_timeout_is_translated(self) -> None:
        def timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timed out", request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
            adapter = SupabaseSessionValidationAdapter(
                client,
                "https://project.supabase.co",
                "publishable-key",
            )
            with self.assertRaises(IdentityProviderUnavailableError):
                await adapter.validate_access_token("session-token")
