import json
import unittest
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from backend.adapters.auth.supabase import (
    GOOGLE_CALENDAR_SCOPE,
    SupabaseGoogleIdentityAdapter,
)
from backend.errors import RedirectNotAllowedError
from backend.schemas.auth import GoogleAuthorizeRequest
from backend.services.identity_auth_service import IdentityAuthService

PKCE_CHALLENGE = "A" * 43


class GoogleAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = SupabaseGoogleIdentityAdapter("https://project.supabase.co/")
        self.service = IdentityAuthService(self.adapter, frozenset({"localhost"}))

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
