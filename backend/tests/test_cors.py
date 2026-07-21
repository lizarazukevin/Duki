import unittest
from dataclasses import replace

from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.main import create_app


class CorsPolicyTests(unittest.TestCase):
    def test_only_configured_origin_receives_browser_access(self) -> None:
        settings = replace(
            get_settings(),
            allowed_cors_origins=("http://localhost:3000",),
        )
        headers = {"Access-Control-Request-Method": "POST"}

        with TestClient(create_app(settings)) as client:
            allowed = client.options(
                "/api/v1/auth/google/authorize",
                headers={**headers, "Origin": "http://localhost:3000"},
            )
            rejected = client.options(
                "/api/v1/auth/google/authorize",
                headers={**headers, "Origin": "https://attacker.example"},
            )

        self.assertEqual(
            allowed.headers["access-control-allow-origin"],
            "http://localhost:3000",
        )
        self.assertNotIn("access-control-allow-origin", rejected.headers)
