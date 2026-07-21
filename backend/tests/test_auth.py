import json
import unittest
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx
from pydantic import ValidationError

from backend.adapters.auth.supabase import (
    GOOGLE_CALENDAR_SCOPE,
    SupabaseAuthorizationCodeExchangeAdapter,
    SupabaseGoogleAuthorizationAdapter,
    SupabaseSessionValidationAdapter,
)
from backend.errors import (
    AuthenticationError,
    AuthorizationExchangeError,
    IdentityProviderUnavailableError,
    RedirectNotAllowedError,
)
from backend.models.auth import AuthenticatedUser, ExchangedSession, GoogleCredentials
from backend.schemas.auth import GoogleAuthorizeRequest, SessionExchangeRequest
from backend.services.identity_authorization_service import (
    IdentityAuthorizationService,
)
from backend.services.session_exchange_service import SessionExchangeService

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
        self.assertEqual(query["access_type"], ["offline"])
        self.assertEqual(query["prompt"], ["consent"])
        self.assertNotIn("query_params", query)

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


class SupabaseAuthorizationCodeExchangeTests(unittest.IsolatedAsyncioTestCase):
    async def test_descriptive_verifier_is_translated_to_supabase_field(self) -> None:
        user_id = uuid4()
        expires_at = 1_800_000_000

        def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.params["grant_type"], "pkce")
            self.assertEqual(request.headers["apikey"], "publishable-key")
            self.assertEqual(
                json.loads(request.content),
                {
                    "auth_code": "authorization-code",
                    "code_verifier": "V" * 43,
                },
            )
            return httpx.Response(
                200,
                json={
                    "access_token": "supabase-access-token",
                    "refresh_token": "supabase-refresh-token",
                    "expires_at": expires_at,
                    "provider_token": "google-access-token",
                    "provider_refresh_token": "google-refresh-token",
                    "user": {
                        "id": str(user_id),
                        "email": "duck@example.com",
                        "user_metadata": {"full_name": "Ducky"},
                    },
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            adapter = SupabaseAuthorizationCodeExchangeAdapter(
                client,
                "https://project.supabase.co",
                "publishable-key",
            )
            session = await adapter.exchange_code("authorization-code", "V" * 43)

        self.assertEqual(session.user.id, user_id)
        self.assertEqual(session.provider_refresh_token, "google-refresh-token")
        self.assertEqual(session.expires_at, datetime.fromtimestamp(expires_at, UTC))

    async def test_invalid_authorization_code_is_translated(self) -> None:
        transport = httpx.MockTransport(lambda request: httpx.Response(400))
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = SupabaseAuthorizationCodeExchangeAdapter(
                client,
                "https://project.supabase.co",
                "publishable-key",
            )
            with self.assertRaises(AuthorizationExchangeError):
                await adapter.exchange_code("invalid-code", "V" * 43)

    async def test_missing_provider_refresh_token_is_an_exchange_error(self) -> None:
        user_id = uuid4()
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "access_token": "supabase-access-token",
                    "refresh_token": "supabase-refresh-token",
                    "expires_at": 1_800_000_000,
                    "provider_token": "google-access-token",
                    "user": {
                        "id": str(user_id),
                        "email": "duck@example.com",
                        "user_metadata": {},
                    },
                },
            )
        )
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = SupabaseAuthorizationCodeExchangeAdapter(
                client,
                "https://project.supabase.co",
                "publishable-key",
            )
            with self.assertRaises(AuthorizationExchangeError):
                await adapter.exchange_code("authorization-code", "V" * 43)

    def test_short_auth_code_verifier_is_rejected_at_boundary(self) -> None:
        with self.assertRaises(ValidationError):
            SessionExchangeRequest.model_validate(
                {
                    "auth_code": "authorization-code",
                    "auth_code_verifier": "too-short",
                }
            )


class _StaticExchangeAdapter:
    def __init__(self, session: ExchangedSession) -> None:
        self.session = session

    async def exchange_code(
        self,
        auth_code: str,
        auth_code_verifier: str,
    ) -> ExchangedSession:
        return self.session


class _RecordingAuthRepository:
    def __init__(self) -> None:
        self.user: AuthenticatedUser | None = None
        self.credentials: GoogleCredentials | None = None

    async def upsert_user(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def save_google_credentials(self, credentials: GoogleCredentials) -> None:
        self.credentials = credentials


class SessionExchangeServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_credentials_are_persisted_before_session_is_returned(self) -> None:
        user = AuthenticatedUser(uuid4(), "duck@example.com", "Ducky", None)
        session = ExchangedSession(
            user=user,
            access_token="supabase-access-token",
            refresh_token="supabase-refresh-token",
            expires_at=datetime.now(UTC),
            provider_access_token="google-access-token",
            provider_refresh_token="google-refresh-token",
        )
        repository = _RecordingAuthRepository()
        service = SessionExchangeService(_StaticExchangeAdapter(session), repository)

        returned_session = await service.exchange("authorization-code", "V" * 43)

        self.assertIs(returned_session, session)
        self.assertIs(repository.user, user)
        self.assertIsNotNone(repository.credentials)
        assert repository.credentials is not None
        self.assertEqual(repository.credentials.refresh_token, "google-refresh-token")
        self.assertIsNone(repository.credentials.access_token_expires_at)
