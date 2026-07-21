import json
from urllib.parse import urlencode

from backend.adapters.auth.base import IdentityAuthAdapter

GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"


class SupabaseGoogleIdentityAdapter(IdentityAuthAdapter):
    """Translate an authorization request into Supabase's Google OAuth URL."""

    def __init__(self, supabase_url: str) -> None:
        self._supabase_url = supabase_url.rstrip("/")

    def build_authorization_url(
        self,
        redirect_to: str,
        code_challenge: str,
    ) -> str:
        parameters = {
            "provider": "google",
            "redirect_to": redirect_to,
            "scopes": GOOGLE_CALENDAR_SCOPE,
            "code_challenge": code_challenge,
            "code_challenge_method": "s256",
            "query_params": json.dumps(
                {"access_type": "offline", "prompt": "consent"},
                separators=(",", ":"),
            ),
        }
        return f"{self._supabase_url}/auth/v1/authorize?{urlencode(parameters)}"
