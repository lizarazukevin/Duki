import unittest
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs
from uuid import uuid4

import httpx
from cryptography.fernet import Fernet

from backend.adapters.calendar.google import GoogleCalendarAdapter
from backend.adapters.security.fernet import FernetCredentialCipher
from backend.errors import CalendarRateLimitError
from backend.models.auth import GoogleCredentials
from backend.repositories.postgres.supabase_auth import SupabaseAuthRepository


class GoogleCredentialRetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def test_stored_credentials_are_decrypted_after_loading(self) -> None:
        user_id = uuid4()
        cipher = FernetCredentialCipher((Fernet.generate_key().decode("ascii"),))

        def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["apikey"], "secret-key")
            self.assertEqual(request.url.params["user_id"], f"eq.{user_id}")
            return httpx.Response(
                200,
                json=[
                    {
                        "encrypted_access_token": cipher.encrypt("google-access-token"),
                        "encrypted_refresh_token": cipher.encrypt("google-refresh-token"),
                        "access_token_expires_at": None,
                    }
                ],
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            repository = SupabaseAuthRepository(
                http_client=client,
                supabase_url="https://project.supabase.co",
                secret_key="secret-key",
                credential_cipher=cipher,
            )
            credentials = await repository.get_google_credentials(user_id)

        self.assertEqual(credentials.access_token, "google-access-token")
        self.assertEqual(credentials.refresh_token, "google-refresh-token")


class GoogleCalendarAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_refreshes_credentials_and_normalizes_all_pages(self) -> None:
        user_id = uuid4()
        page_requests = 0

        def respond(request: httpx.Request) -> httpx.Response:
            nonlocal page_requests
            if request.url.host == "oauth2.googleapis.com":
                form = parse_qs(request.content.decode("ascii"))
                self.assertEqual(form["client_id"], ["google-client-id"])
                self.assertEqual(form["client_secret"], ["google-client-secret"])
                self.assertEqual(form["refresh_token"], ["google-refresh-token"])
                return httpx.Response(
                    200,
                    json={"access_token": "fresh-access-token", "expires_in": 3600},
                )

            page_requests += 1
            self.assertEqual(request.headers["authorization"], "Bearer fresh-access-token")
            self.assertEqual(request.url.params["showDeleted"], "true")
            self.assertEqual(request.url.params["singleEvents"], "true")
            if page_requests == 1:
                self.assertNotIn("pageToken", request.url.params)
                return httpx.Response(
                    200,
                    json={
                        "timeZone": "UTC",
                        "nextPageToken": "second-page",
                        "items": [
                            {
                                "id": "timed-event",
                                "status": "confirmed",
                                "summary": "Planning",
                                "start": {"dateTime": "2026-07-22T14:00:00Z"},
                                "end": {"dateTime": "2026-07-22T15:00:00Z"},
                                "updated": "2026-07-21T16:00:00Z",
                            },
                            {"id": "deleted-event", "status": "cancelled"},
                        ],
                    },
                )
            self.assertEqual(request.url.params["pageToken"], "second-page")
            return httpx.Response(
                200,
                json={
                    "timeZone": "UTC",
                    "items": [
                        {
                            "id": "all-day-event",
                            "status": "tentative",
                            "start": {"date": "2026-07-23"},
                            "end": {"date": "2026-07-24"},
                            "updated": "2026-07-21T17:00:00Z",
                            "transparency": "transparent",
                        }
                    ],
                },
            )

        credentials = GoogleCredentials(
            user_id=user_id,
            access_token="expired-access-token",
            refresh_token="google-refresh-token",
            access_token_expires_at=None,
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            adapter = GoogleCalendarAdapter(
                client,
                client_id="google-client-id",
                client_secret="google-client-secret",
            )
            result = await adapter.list_events(
                credentials=credentials,
                start_time=datetime(2026, 7, 21, tzinfo=UTC),
                end_time=datetime(2026, 7, 28, tzinfo=UTC),
            )

        self.assertEqual(page_requests, 2)
        self.assertEqual(
            [event.provider_event_id for event in result.events],
            [
                "timed-event",
                "all-day-event",
            ],
        )
        self.assertTrue(result.events[1].is_all_day)
        self.assertEqual(result.events[1].title, "Busy")
        self.assertEqual(result.cancelled_event_ids, ("deleted-event",))
        self.assertIsNotNone(result.refreshed_credentials)
        assert result.refreshed_credentials is not None
        self.assertEqual(result.refreshed_credentials.access_token, "fresh-access-token")

    async def test_rate_limit_is_translated_to_domain_error(self) -> None:
        def respond(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                403,
                json={
                    "error": {
                        "errors": [{"reason": "rateLimitExceeded"}],
                    }
                },
            )

        credentials = GoogleCredentials(
            user_id=uuid4(),
            access_token="active-access-token",
            refresh_token="google-refresh-token",
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            adapter = GoogleCalendarAdapter(client, "google-client-id", "google-client-secret")
            with self.assertRaises(CalendarRateLimitError):
                await adapter.list_events(
                    credentials,
                    datetime(2026, 7, 21, tzinfo=UTC),
                    datetime(2026, 7, 28, tzinfo=UTC),
                )
